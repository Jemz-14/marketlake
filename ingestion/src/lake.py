"""Bronze-layer lake writer.

Writes tidy DataFrames to a Hive-style partitioned Parquet layout that mirrors
what we'll later land in ADLS Gen2:

    <lake_root>/bronze/<source>/date=YYYY-MM-DD/<source>.parquet

One file per date partition. Writing a partition fully overwrites it, so the
job is idempotent: re-running the same window reproduces the same lake state
rather than appending duplicates.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def bronze_partition_path(
    lake_root: str | Path, source: str, partition_date: str, filename: str | None = None
) -> Path:
    """Path of a Parquet file inside one source + date partition.

    `filename` lets several entities (e.g. one per ticker) coexist in the same
    date partition as separate part-files -- the standard multi-file lake layout.
    Defaults to "<source>.parquet" (a single file per partition).
    """
    return (
        Path(lake_root)
        / "bronze"
        / source
        / f"date={partition_date}"
        / (filename or f"{source}.parquet")
    )


def write_partitioned(
    df: pd.DataFrame,
    lake_root: str | Path,
    source: str,
    partition_col: str,
    filename: str | None = None,
) -> list[Path]:
    """Split df by `partition_col` (a YYYY-MM-DD column) and write one Parquet
    file per date partition. Returns the paths written.

    Used for time-series sources (prices, fx) where each row belongs to a
    business date and a single run may span several dates. Pass `filename` to
    keep per-entity slices separate within a partition (prices does this per
    ticker, so loading one ticker never overwrites another's rows for that day).
    """
    if df.empty:
        return []
    if partition_col not in df.columns:
        raise KeyError(f"partition_col {partition_col!r} not in DataFrame columns {list(df.columns)}")

    written: list[Path] = []
    for partition_date, group in df.groupby(partition_col, sort=True):
        path = bronze_partition_path(lake_root, source, str(partition_date), filename)
        _write_parquet(group, path)
        written.append(path)
        logger.info("Wrote %d rows -> %s", len(group), path)
    return written


def write_snapshot(
    df: pd.DataFrame, lake_root: str | Path, source: str, partition_date: str
) -> Path | None:
    """Write the whole df into a single date partition.

    Used for snapshot sources (fundamentals) that have no natural business date
    -- we partition by the run/snapshot date instead.
    """
    if df.empty:
        return None
    path = bronze_partition_path(lake_root, source, partition_date)
    _write_parquet(df, path)
    logger.info("Wrote %d rows -> %s", len(df), path)
    return path


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", index=False)
