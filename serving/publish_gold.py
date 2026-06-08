"""Publish the gold layer from Azure SQL to ADLS Gen2 as Parquet.

Synapse serverless reads files in storage (not Azure SQL tables), so this is the
bridge: read each gold table, write Parquet, upload to

    <data filesystem>/gold/<table>/<table>.parquet

Idempotent — every run overwrites. Credentials come from the repo-root .env
(the MARKETLAKE_SQL_* warehouse vars plus MARKETLAKE_STORAGE_* for the lake).
"""
from __future__ import annotations

import io
import logging
import os

import pandas as pd
from azure.storage.filedatalake import DataLakeServiceClient
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

logger = logging.getLogger("marketlake.publish")

GOLD_TABLES = (
    "dim_date",
    "dim_security",
    "dim_sector",
    "fact_daily_price",
    "fact_price_indicators",
)


def _engine():
    url = URL.create(
        "mssql+pyodbc",
        username=os.environ["MARKETLAKE_SQL_USER"],
        password=os.environ["MARKETLAKE_SQL_PASSWORD"],
        host=os.environ["MARKETLAKE_SQL_SERVER"],
        port=1433,
        database=os.environ["MARKETLAKE_SQL_DATABASE"],
        query={
            "driver": "ODBC Driver 18 for SQL Server",
            "Encrypt": "yes",
            "TrustServerCertificate": "no",
            "Connection Timeout": "60",
        },
    )
    return create_engine(url)


def _filesystem():
    account = os.environ["MARKETLAKE_STORAGE_ACCOUNT"]
    key = os.environ["MARKETLAKE_STORAGE_KEY"]
    fs_name = os.environ.get("MARKETLAKE_STORAGE_FILESYSTEM", "data")
    service = DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net", credential=key
    )
    return service.get_file_system_client(fs_name), fs_name


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )
    load_dotenv(find_dotenv(usecwd=True))

    engine = _engine()
    fs, fs_name = _filesystem()

    for table in GOLD_TABLES:
        df = pd.read_sql(text(f"SELECT * FROM gold.{table}"), engine)
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", index=False)
        payload = buf.getvalue()

        path = f"gold/{table}/{table}.parquet"
        fs.get_file_client(path).upload_data(payload, overwrite=True)
        logger.info("published gold.%s -> %s/%s (%d rows, %d bytes)",
                    table, fs_name, path, len(df), len(payload))

    logger.info("Publish done | %d tables -> %s", len(GOLD_TABLES), fs_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
