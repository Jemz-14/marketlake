"""Load and validate the ingestion control table (config/sources.json).

This is the local stand-in for the ADF metadata/control table: the list of
tickers and source settings that drive the job. Keeping it as data (not code)
is the point -- adding a ticker is a one-line edit here, no code change.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


class ConfigError(ValueError):
    """Raised when the control table is missing required fields or malformed."""


def load_config(path: str | Path) -> dict:
    """Read sources.json and return a validated config dict."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {path} ({exc})") from exc

    _validate(cfg, path)
    return cfg


def _validate(cfg: dict, path: Path) -> None:
    tickers = cfg.get("tickers")
    if not isinstance(tickers, list) or not tickers:
        raise ConfigError(f"'tickers' must be a non-empty list in {path}")

    default_start = cfg.get("default_start")
    if not _is_iso_date(default_start):
        raise ConfigError(
            f"'default_start' must be a YYYY-MM-DD date in {path}, got {default_start!r}"
        )

    fx = cfg.get("fx", {})
    if not isinstance(fx, dict) or not fx.get("base") or not fx.get("quotes"):
        raise ConfigError(f"'fx' must have a 'base' and non-empty 'quotes' list in {path}")


def _is_iso_date(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
