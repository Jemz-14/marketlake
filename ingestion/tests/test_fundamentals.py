"""Fundamentals extractor tests -- fake yfinance, no network."""
import sys
import types

from src.sources.fundamentals import fetch_fundamentals


class _FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    @property
    def info(self):
        if self.symbol == "BAD":
            raise RuntimeError("simulated network failure")
        return {
            "longName": f"{self.symbol} Inc",
            "sector": "Technology",
            "industry": "Software",
            "marketCap": 123_000,
            "currency": "USD",
            "exchange": "NMS",
            "country": "United States",
            "quoteType": "EQUITY",
        }


def _install_fake_yf(monkeypatch):
    fake = types.ModuleType("yfinance")
    fake.Ticker = _FakeTicker
    monkeypatch.setitem(sys.modules, "yfinance", fake)


def test_one_row_per_ticker_with_expected_columns(monkeypatch):
    _install_fake_yf(monkeypatch)
    df = fetch_fundamentals(["AAPL", "MSFT"], snapshot_date="2026-06-06")

    assert len(df) == 2
    assert set(df.columns) >= {
        "ticker", "long_name", "sector", "industry", "market_cap",
        "currency", "snapshot_date", "_source", "_ingested_at",
    }
    assert (df["snapshot_date"] == "2026-06-06").all()
    assert (df["_source"] == "fundamentals").all()


def test_failing_ticker_is_skipped_not_fatal(monkeypatch):
    _install_fake_yf(monkeypatch)
    df = fetch_fundamentals(["AAPL", "BAD", "MSFT"], snapshot_date="2026-06-06")

    assert sorted(df["ticker"]) == ["AAPL", "MSFT"]  # BAD dropped, run survived
