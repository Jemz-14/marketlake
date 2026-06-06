"""MarketLake ingestion job: SOURCES -> bronze lake (Phase 1).

Orchestrates the three extractors and lands their output as partitioned Parquet
in the local bronze lake. Demonstrates the two patterns that matter for the
cloud version:

  * metadata-driven   -- the ticker list comes from config/sources.json (the
                         control table), so adding a ticker is a data change.
  * incremental       -- a per-source/per-ticker high-water-mark means each run
                         pulls only new dates and can be safely re-run.

Usage (from the ingestion/ directory):

    python extract.py                       # all sources, incremental, lake at ./_lake
    python extract.py --sources prices fx   # subset
    python extract.py --full-refresh        # ignore watermark, re-pull from default_start
    python extract.py --end 2026-05-30      # pull up to a fixed date
    python extract.py --lake-root /tmp/lake --log-level DEBUG
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date

# Make `src` importable no matter what directory the job is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config  # noqa: E402
from src.lake import write_partitioned, write_snapshot  # noqa: E402
from src.sources.fundamentals import fetch_fundamentals  # noqa: E402
from src.sources.fx import fetch_fx  # noqa: E402
from src.sources.prices import fetch_prices  # noqa: E402
from src.watermark import load_watermarks, next_start, save_watermarks  # noqa: E402

logger = logging.getLogger("marketlake.ingest")

ALL_SOURCES = ("prices", "fx", "fundamentals")
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(_HERE, "config", "sources.json")


def _safe(ticker: str) -> str:
    """Make a ticker safe to use as a filename (e.g. 'BHP.AX' -> 'BHP_AX')."""
    return "".join(c if c.isalnum() else "_" for c in ticker)


def run_prices(cfg, watermarks, lake_root, end_date, full_refresh) -> int:
    """Incremental per-ticker load of daily OHLCV prices. Returns rows written."""
    wm = watermarks.setdefault("prices", {})
    default_start = cfg["default_start"]
    total = 0

    # Metadata-driven ForEach: loop the control-table tickers, each with its own
    # watermark so a newly added ticker backfills while existing ones stay incremental.
    for ticker in cfg["tickers"]:
        last = None if full_refresh else wm.get(ticker)
        start = next_start(last, default_start)
        if start > end_date:
            logger.info("prices: %s already up to date (watermark %s)", ticker, last)
            continue

        df = fetch_prices([ticker], start, end_date)
        if df.empty:
            logger.info("prices: no new rows for %s in [%s, %s]", ticker, start, end_date)
            continue

        # One part-file per ticker inside each date partition, so loading this
        # ticker never overwrites another ticker's rows for the same day.
        write_partitioned(
            df, lake_root, "prices", partition_col="trade_date",
            filename=f"prices-{_safe(ticker)}.parquet",
        )
        wm[ticker] = df["trade_date"].max()  # advance only after a successful write
        total += len(df)

    return total


def run_fx(cfg, watermarks, lake_root, end_date, full_refresh) -> int:
    """Incremental load of FX rates. Returns rows written."""
    fx_cfg = cfg["fx"]
    last = None if full_refresh else watermarks.get("fx")
    start = next_start(last, cfg["default_start"])
    if start > end_date:
        logger.info("fx: already up to date (watermark %s)", last)
        return 0

    df = fetch_fx(fx_cfg["base"], fx_cfg["quotes"], start, end_date)
    if df.empty:
        logger.info("fx: no new rows in [%s, %s]", start, end_date)
        return 0

    write_partitioned(df, lake_root, "fx", partition_col="rate_date")
    watermarks["fx"] = df["rate_date"].max()
    return len(df)


def run_fundamentals(cfg, watermarks, lake_root, run_date) -> int:
    """Snapshot load of company fundamentals into the run-date partition.

    Idempotent per day: if we already snapshotted today, skip (re-running the
    job won't duplicate or thrash the partition).
    """
    if watermarks.get("fundamentals") == run_date:
        logger.info("fundamentals: snapshot for %s already taken, skipping", run_date)
        return 0

    df = fetch_fundamentals(cfg["tickers"], snapshot_date=run_date)
    if df.empty:
        logger.info("fundamentals: no rows returned")
        return 0

    write_snapshot(df, lake_root, "fundamentals", partition_date=run_date)
    watermarks["fundamentals"] = run_date
    return len(df)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )

    run_date = date.today().isoformat()
    end_date = args.end or run_date
    cfg = load_config(args.config)
    watermarks = load_watermarks(args.lake_root)

    logger.info(
        "Ingest start | sources=%s | end=%s | lake=%s | full_refresh=%s",
        ",".join(args.sources), end_date, args.lake_root, args.full_refresh,
    )

    summary: dict[str, int] = {}
    if "prices" in args.sources:
        summary["prices"] = run_prices(cfg, watermarks, args.lake_root, end_date, args.full_refresh)
    if "fx" in args.sources:
        summary["fx"] = run_fx(cfg, watermarks, args.lake_root, end_date, args.full_refresh)
    if "fundamentals" in args.sources:
        summary["fundamentals"] = run_fundamentals(cfg, watermarks, args.lake_root, run_date)

    # Persist the advanced watermarks only at the very end -- one consistent save.
    save_watermarks(args.lake_root, watermarks)

    logger.info("Ingest done | rows written: %s",
                ", ".join(f"{k}={v}" for k, v in summary.items()) or "none")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MarketLake ingestion -> bronze lake")
    p.add_argument("--sources", nargs="+", choices=ALL_SOURCES, default=list(ALL_SOURCES),
                   help="Which sources to run (default: all).")
    p.add_argument("--end", metavar="YYYY-MM-DD", default=None,
                   help="Inclusive end date for the pull (default: today).")
    p.add_argument("--lake-root", default="_lake",
                   help="Root of the local lake (default: ./_lake).")
    p.add_argument("--config", default=DEFAULT_CONFIG,
                   help="Path to the control table (default: config/sources.json).")
    p.add_argument("--full-refresh", action="store_true",
                   help="Ignore watermarks and re-pull from default_start.")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Logging verbosity (default: INFO).")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
