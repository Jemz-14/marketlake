"""Load the local bronze Parquet lake into the Azure SQL `bronze` schema.

This is the EL step before dbt's T: each bronze source is mirrored as a raw
table (bronze.prices, bronze.fx, bronze.fundamentals) that dbt's staging models
read from. In the cloud this is an ADF Copy activity; here it's a small Python
job so Phase 2 runs end-to-end locally.

Idempotent: each source table is fully replaced from the lake on every run, so
re-running reproduces warehouse state rather than duplicating rows.

Usage (from the ingestion/ directory, with .env filled in):
    python load_bronze.py                     # all sources
    python load_bronze.py --sources prices fx
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import sys

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.warehouse import get_engine  # noqa: E402

logger = logging.getLogger("marketlake.load")

SOURCES = ("prices", "fx", "fundamentals")
SCHEMA = "bronze"


def read_source(lake_root: str, source: str) -> pd.DataFrame:
    """Union all Parquet part-files for one source into a single DataFrame."""
    pattern = os.path.join(lake_root, "bronze", source, "**", "*.parquet")
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        return pd.DataFrame()
    return pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)


def ensure_schema(engine, schema: str = SCHEMA) -> None:
    # CREATE SCHEMA must be the first statement in a batch, so wrap it in EXEC.
    with engine.begin() as cn:
        cn.execute(
            text(
                "IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = :s) "
                f"EXEC('CREATE SCHEMA [{schema}]')"
            ),
            {"s": schema},
        )


def load_source(engine, df: pd.DataFrame, source: str, schema: str = SCHEMA) -> int:
    df.to_sql(source, engine, schema=schema, if_exists="replace", index=False, chunksize=500)
    return len(df)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )

    engine = get_engine()
    ensure_schema(engine)
    logger.info("Connected; ensured schema [%s].", SCHEMA)

    summary: dict[str, int] = {}
    for source in args.sources:
        df = read_source(args.lake_root, source)
        if df.empty:
            logger.warning("load: no parquet found for %s under %s", source, args.lake_root)
            summary[source] = 0
            continue
        n = load_source(engine, df, source)
        logger.info("load: %s.%s <- %d rows (%d cols)", SCHEMA, source, n, df.shape[1])
        summary[source] = n

    logger.info("Load done | %s", ", ".join(f"{k}={v}" for k, v in summary.items()))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Load bronze Parquet -> Azure SQL bronze schema")
    p.add_argument("--sources", nargs="+", choices=SOURCES, default=list(SOURCES),
                   help="Which sources to load (default: all).")
    p.add_argument("--lake-root", default=os.environ.get("LAKE_ROOT", "_lake"),
                   help="Root of the local lake (default: $LAKE_ROOT, else ./_lake).")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
