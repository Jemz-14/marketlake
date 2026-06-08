"""Set up the Synapse serverless serving layer (idempotent).

Creates a serving database on the serverless SQL pool, a managed-identity
credential + external data source over the ADLS `data` filesystem, and one view
per gold table (OPENROWSET over the published Parquet). Re-runnable.

Env (repo-root .env):
  MARKETLAKE_SYNAPSE_SERVER    <workspace>-ondemand.sql.azuresynapse.net
  MARKETLAKE_SYNAPSE_USER      synapse SQL admin login
  MARKETLAKE_SYNAPSE_PASSWORD  synapse SQL admin password
  MARKETLAKE_STORAGE_ACCOUNT   ADLS Gen2 account name
"""
from __future__ import annotations

import logging
import os
import secrets
import time

import pyodbc
from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger("marketlake.synapse")

SERVING_DB = "marketlake_serving"
GOLD_TABLES = (
    "dim_date",
    "dim_security",
    "dim_sector",
    "fact_daily_price",
    "fact_price_indicators",
)


def _connect(database: str) -> pyodbc.Connection:
    server = os.environ["MARKETLAKE_SYNAPSE_SERVER"]
    cs = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{server},1433;DATABASE={database};"
        f"UID={os.environ['MARKETLAKE_SYNAPSE_USER']};"
        f"PWD={os.environ['MARKETLAKE_SYNAPSE_PASSWORD']};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )
    return pyodbc.connect(cs, autocommit=True)  # DDL like CREATE DATABASE needs autocommit


def _exists(cur, sql: str, params=()) -> bool:
    cur.execute(sql, params)
    return cur.fetchone() is not None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s")
    load_dotenv(find_dotenv(usecwd=True))
    account = os.environ["MARKETLAKE_STORAGE_ACCOUNT"]

    # 1) Serving database (in master). A freshly-created Synapse workspace holds
    #    a transient lock on the system 'model' db (error 1807); retry through it.
    for attempt in range(1, 13):
        try:
            with _connect("master") as cn:
                cur = cn.cursor()
                if not _exists(cur, "SELECT 1 FROM sys.databases WHERE name = ?", (SERVING_DB,)):
                    cur.execute(f"CREATE DATABASE [{SERVING_DB}]")
                    logger.info("created database %s", SERVING_DB)
                else:
                    logger.info("database %s already exists", SERVING_DB)
            break
        except pyodbc.Error as exc:
            transient = "1807" in str(exc) or "Retry the operation later" in str(exc)
            if transient and attempt < 12:
                logger.warning("model db still locked (workspace settling), retry %d/12 in 20s...", attempt)
                time.sleep(20)
                continue
            raise

    # 2) Credential + data source + views (in the serving database).
    with _connect(SERVING_DB) as cn:
        cur = cn.cursor()

        if not _exists(cur, "SELECT 1 FROM sys.symmetric_keys WHERE name = '##MS_DatabaseMasterKey##'"):
            cur.execute(f"CREATE MASTER KEY ENCRYPTION BY PASSWORD = '{secrets.token_urlsafe(24)}'")
            logger.info("created master key")

        if not _exists(cur, "SELECT 1 FROM sys.database_scoped_credentials WHERE name = 'synapse_msi'"):
            cur.execute("CREATE DATABASE SCOPED CREDENTIAL synapse_msi WITH IDENTITY = 'Managed Identity'")
            logger.info("created managed-identity credential")

        if not _exists(cur, "SELECT 1 FROM sys.external_data_sources WHERE name = 'gold_lake'"):
            cur.execute(
                "CREATE EXTERNAL DATA SOURCE gold_lake WITH ("
                f"LOCATION = 'https://{account}.dfs.core.windows.net/data', "
                "CREDENTIAL = synapse_msi)"
            )
            logger.info("created external data source gold_lake")

        for table in GOLD_TABLES:
            cur.execute(
                f"CREATE OR ALTER VIEW dbo.{table} AS "
                f"SELECT * FROM OPENROWSET(BULK 'gold/{table}/', "
                "DATA_SOURCE = 'gold_lake', FORMAT = 'PARQUET') AS r"
            )
            n = cur.execute(f"SELECT COUNT(*) FROM dbo.{table}").fetchone()[0]
            logger.info("view dbo.%s ready (%d rows)", table, n)

    logger.info("Synapse serving layer ready: db=%s, %d views", SERVING_DB, len(GOLD_TABLES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
