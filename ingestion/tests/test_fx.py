"""FX extractor tests -- the two Frankfurter response shapes, no network."""
from src.sources import fx


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _patch_get(monkeypatch, payload):
    monkeypatch.setattr(fx.requests, "get", lambda *a, **k: _FakeResp(payload))


def test_single_day_shape(monkeypatch):
    _patch_get(monkeypatch, {"date": "2026-05-29", "rates": {"USD": 0.66, "EUR": 0.61}})
    df = fx.fetch_fx("AUD", ["USD", "EUR"], "2026-05-29", "2026-05-29")

    assert set(df.columns) >= {"rate_date", "base_currency", "quote_currency", "rate", "_source"}
    assert len(df) == 2
    assert (df["rate_date"] == "2026-05-29").all()
    assert (df["base_currency"] == "AUD").all()
    assert set(df["quote_currency"]) == {"USD", "EUR"}


def test_single_day_uses_payload_date_not_request_date(monkeypatch):
    # request a weekend; API answers with Friday's data + Friday's date
    _patch_get(monkeypatch, {"date": "2026-06-05", "rates": {"USD": 0.65}})
    df = fx.fetch_fx("AUD", ["USD"], "2026-06-06", "2026-06-06")

    assert (df["rate_date"] == "2026-06-05").all()  # not the requested 06-06


def test_date_range_shape(monkeypatch):
    _patch_get(monkeypatch, {
        "rates": {
            "2026-05-28": {"USD": 0.66},
            "2026-05-29": {"USD": 0.65},
        }
    })
    df = fx.fetch_fx("AUD", ["USD"], "2026-05-28", "2026-05-29")

    assert len(df) == 2
    assert set(df["rate_date"]) == {"2026-05-28", "2026-05-29"}


def test_empty_rates_returns_empty_df(monkeypatch):
    _patch_get(monkeypatch, {"rates": {}})
    assert fx.fetch_fx("AUD", ["USD"], "2026-05-29", "2026-05-29").empty
