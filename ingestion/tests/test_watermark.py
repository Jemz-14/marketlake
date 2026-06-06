from src.watermark import load_watermarks, next_start, save_watermarks


def test_next_start_no_watermark_uses_default():
    assert next_start(None, "2026-03-01") == "2026-03-01"
    assert next_start("", "2026-03-01") == "2026-03-01"


def test_next_start_is_day_after_watermark():
    # inclusive ranges: never re-pull the last loaded day
    assert next_start("2026-05-29", "2026-03-01") == "2026-05-30"
    # crosses a month boundary correctly
    assert next_start("2026-05-31", "2026-03-01") == "2026-06-01"


def test_watermark_roundtrip(tmp_path):
    wm = {"prices": {"AAPL": "2026-05-29"}, "fx": "2026-05-29"}
    save_watermarks(tmp_path, wm)
    assert load_watermarks(tmp_path) == wm


def test_load_missing_returns_empty(tmp_path):
    assert load_watermarks(tmp_path) == {}


def test_load_corrupt_returns_empty(tmp_path):
    path = tmp_path / "_state" / "watermarks.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not valid json", encoding="utf-8")
    assert load_watermarks(tmp_path) == {}
