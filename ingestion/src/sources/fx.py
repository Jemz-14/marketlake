"""Source: FX rates, for normalising values to AUD later.

Uses the free, key-less Frankfurter API (ECB reference rates, business days only).
Returns a tidy DataFrame: one row per (rate_date, base_currency, quote_currency).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.frankfurter.app"


def fetch_fx(base: str, quotes: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    if not quotes:
        raise ValueError("fx source requires at least one quote currency.")

    # Single day vs date-range use different Frankfurter endpoints.
    if start_date == end_date:
        url = f"{_BASE_URL}/{start_date}"
    else:
        url = f"{_BASE_URL}/{start_date}..{end_date}"
    params = {"from": base, "to": ",".join(quotes)}

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    ingested_at = datetime.now(timezone.utc).isoformat()
    raw_rates = payload.get("rates", {})

    rows: list[dict] = []
    if start_date == end_date:
        # shape: {"date": "2026-06-05", "rates": {"AUD": 1.52, ...}}
        # Frankfurter returns the most recent business day on/before the request,
        # so trust the payload's own date -- a weekend/holiday run must not label
        # Friday's rates with Saturday's date.
        actual_date = payload.get("date", start_date)
        for quote, rate in raw_rates.items():
            rows.append(_row(actual_date, base, quote, rate, ingested_at))
    else:
        # shape: {"rates": {"2026-01-02": {"AUD": 1.52, ...}, ...}}
        for rate_date, quote_map in raw_rates.items():
            for quote, rate in quote_map.items():
                rows.append(_row(rate_date, base, quote, rate, ingested_at))

    if not rows:
        logger.warning("No FX rows returned for %s->%s in [%s, %s]", base, quotes, start_date, end_date)
        return pd.DataFrame()

    logger.info("Fetched %d FX rows (%s -> %s)", len(rows), base, ",".join(quotes))
    return pd.DataFrame(rows)


def _row(rate_date: str, base: str, quote: str, rate, ingested_at: str) -> dict:
    return {
        "rate_date": rate_date,
        "base_currency": base,
        "quote_currency": quote,
        "rate": rate,
        "_source": "fx",
        "_ingested_at": ingested_at,
    }
