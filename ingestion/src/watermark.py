"""High-water-mark state for incremental loading.

The watermark records the last successfully loaded date per source (and, for
prices, per ticker). On each run we pull only data *after* the watermark, then
advance it -- so re-running is cheap and a crash never loses ground.

State lives in the lake at <lake_root>/_state/watermarks.json. It's operational
state, not source data, so it sits alongside (not inside) the bronze tree.

Shape:
    {
      "prices": {"AAPL": "2026-05-29", "MSFT": "2026-05-29"},
      "fx": "2026-05-29",
      "fundamentals": "2026-06-06"
    }
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def watermark_path(lake_root: str | Path) -> Path:
    return Path(lake_root) / "_state" / "watermarks.json"


def load_watermarks(lake_root: str | Path) -> dict:
    path = watermark_path(lake_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Watermark file is corrupt, starting fresh: %s", path)
        return {}


def save_watermarks(lake_root: str | Path, watermarks: dict) -> None:
    path = watermark_path(lake_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(watermarks, indent=2, sort_keys=True), encoding="utf-8")
    logger.debug("Saved watermarks -> %s", path)


def next_start(last_loaded: str | None, default_start: str) -> str:
    """The first date to pull on this run.

    If we have a watermark, start the day *after* it (inclusive ranges, no
    re-pulling the last day). Otherwise fall back to the configured backfill
    start. This is the core incremental rule.
    """
    if not last_loaded:
        return default_start
    return (date.fromisoformat(last_loaded) + timedelta(days=1)).isoformat()
