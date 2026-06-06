"""SQLAlchemy engine for the Azure SQL warehouse.

Configured entirely from environment variables (loaded from a `.env` at the
repo root). The bronze loader uses this; dbt has its own profiles.yml that
reads the same env vars, so credentials live in exactly one place.
"""
from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

_REQUIRED = (
    "MARKETLAKE_SQL_SERVER",
    "MARKETLAKE_SQL_DATABASE",
    "MARKETLAKE_SQL_USER",
    "MARKETLAKE_SQL_PASSWORD",
)


def get_engine() -> Engine:
    """Build a SQLAlchemy engine for Azure SQL from env vars (.env at repo root)."""
    load_dotenv(find_dotenv(usecwd=True))

    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            "Missing warehouse env vars: " + ", ".join(missing) + ". "
            "Copy .env.example to .env and fill it in (password via "
            "`cd infra; terraform output -raw sql_admin_password`)."
        )

    # Let SQLAlchemy build and escape the URL. URL.create handles special
    # characters in the password correctly, unlike a hand-encoded
    # odbc_connect string.
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
