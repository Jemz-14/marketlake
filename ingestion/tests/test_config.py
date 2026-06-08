"""Control-table loader / validation tests."""
import json

import pytest
from src.config import ConfigError, load_config


def _write(tmp_path, payload):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loads_valid_config(tmp_path):
    path = _write(tmp_path, {
        "default_start": "2026-03-01",
        "tickers": ["AAPL"],
        "fx": {"base": "AUD", "quotes": ["USD"]},
    })
    cfg = load_config(path)
    assert cfg["tickers"] == ["AAPL"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_empty_tickers_raises(tmp_path):
    path = _write(tmp_path, {
        "default_start": "2026-03-01", "tickers": [],
        "fx": {"base": "AUD", "quotes": ["USD"]},
    })
    with pytest.raises(ConfigError):
        load_config(path)


def test_bad_default_start_raises(tmp_path):
    path = _write(tmp_path, {
        "default_start": "March", "tickers": ["AAPL"],
        "fx": {"base": "AUD", "quotes": ["USD"]},
    })
    with pytest.raises(ConfigError):
        load_config(path)


def test_missing_fx_raises(tmp_path):
    path = _write(tmp_path, {"default_start": "2026-03-01", "tickers": ["AAPL"]})
    with pytest.raises(ConfigError):
        load_config(path)
