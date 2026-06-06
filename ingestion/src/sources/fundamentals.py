"""Source: company reference / fundamentals (a dimension source).

Pulls descriptive attributes per ticker -- sector, industry, market cap,
listing currency/exchange -- from Yahoo Finance via yfinance. Unlike prices,
this has no natural per-day grain: it's a point-in-time *snapshot* of what each
company looks like today. The orchestrator partitions it by the run date so we
keep a daily history of how these attributes drift (cheap slowly-changing
dimension input for the gold layer later).

Returns one row per ticker.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

# yfinance .info key -> our column name. Kept explicit so a change in Yahoo's
# payload surfaces as a missing (null) column rather than a silent schema drift.
_FIELDS = {
    "longName": "long_name",
    "sector": "sector",
    "industry": "industry",
    "marketCap": "market_cap",
    "currency": "currency",
    "exchange": "exchange",
    "country": "country",
    "quoteType": "quote_type",
}


def fetch_fundamentals(tickers: list[str], snapshot_date: str | None = None) -> pd.DataFrame:
    import yfinance as yf

    if not tickers:
        raise ValueError("fundamentals source requires at least one ticker.")

    snapshot_date = snapshot_date or date.today().isoformat()
    ingested_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
        except Exception as exc:  # network / API hiccup -- skip, don't kill the run
            logger.error("Fundamentals fetch failed for %s: %s", ticker, exc)
            continue

        if not info:
            logger.warning("No fundamentals returned for %s", ticker)
            continue

        row = {"ticker": ticker}
        row.update({col: info.get(src_key) for src_key, col in _FIELDS.items()})
        row["snapshot_date"] = snapshot_date
        row["_source"] = "fundamentals"
        row["_ingested_at"] = ingested_at
        rows.append(row)
        logger.info("Fetched fundamentals for %s (%s / %s)", ticker, row["sector"], row["industry"])

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)
