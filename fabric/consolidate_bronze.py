"""Consolidate the partitioned local bronze lake into ONE Parquet file per
source, for easy upload to the Microsoft Fabric Lakehouse (Files/bronze/).

    python fabric/consolidate_bronze.py   # writes fabric/bronze_upload/*.parquet
"""
from __future__ import annotations

import glob
import os

import pandas as pd

LAKE = os.path.join("ingestion", "_lake", "bronze")
OUT = os.path.join("fabric", "bronze_upload")
SOURCES = ("prices", "fx", "fundamentals")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for source in SOURCES:
        files = sorted(glob.glob(os.path.join(LAKE, source, "**", "*.parquet"), recursive=True))
        df = pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)
        out = os.path.join(OUT, f"{source}.parquet")
        df.to_parquet(out, engine="pyarrow", index=False)
        print(f"{source}: {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
