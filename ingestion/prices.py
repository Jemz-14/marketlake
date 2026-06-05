"""Source: daily OHLCV prices (the fact source).

Pulls per-ticker daily bars from Yahoo Finance via yfinance and returns one tidy
(long) DataFrame. yfinance treats `end` as EXCLUSIVE, so we add a day internally
to make the caller-facing end date inclusive.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import pandas as pd

logger = logging.getLogger(__name__)

_RENAME = {
    "Date": "trade_date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}


def _inclusive_end(end_date: str) -> str:
    d = date.fromisoformat(end_date) + timedelta(days=1)
    return d.isoformat()


def fetch_prices(tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    import yfinance as yf

    if not tickers:
        raise ValueError("prices source requires at least one ticker.")

    end_excl = _inclusive_end(end_date)
    ingested_at = datetime.now(timezone.utc).isoformat()
    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(
                start=start_date, end=end_excl, auto_adjust=False, actions=False
            )
        except Exception as exc:  # network / API hiccup -- skip, don't kill the run
            logger.error("Price fetch failed for %s: %s", ticker, exc)
            continue

        if hist is None or hist.empty:
            logger.warning("No price rows for %s in [%s, %s)", ticker, start_date, end_excl)
            continue

        hist = hist.reset_index().rename(columns=_RENAME)
        # Date may be tz-aware; keep just the calendar date.
        hist["trade_date"] = pd.to_datetime(hist["trade_date"]).dt.date.astype(str)
        keep = [c for c in _RENAME.values() if c in hist.columns]
        hist = hist[keep].copy()
        hist.insert(0, "ticker", ticker)
        hist["_source"] = "prices"
        hist["_ingested_at"] = ingested_at
        frames.append(hist)
        logger.info("Fetched %d price rows for %s", len(hist), ticker)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
