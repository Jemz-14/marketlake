import pandas as pd
from src.lake import bronze_partition_path, write_partitioned, write_snapshot


def _prices_df():
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT"],
            "trade_date": ["2026-05-28", "2026-05-29", "2026-05-29"],
            "close": [312.5, 312.0, 430.1],
        }
    )


def test_write_partitioned_creates_one_file_per_date(tmp_path):
    written = write_partitioned(_prices_df(), tmp_path, "prices", "trade_date")

    # two distinct trade dates -> two partitions
    assert len(written) == 2
    p28 = bronze_partition_path(tmp_path, "prices", "2026-05-28")
    p29 = bronze_partition_path(tmp_path, "prices", "2026-05-29")
    assert p28.exists() and p29.exists()
    assert "bronze" in p28.parts and "date=2026-05-28" in p28.parts

    # the 2026-05-29 partition holds both AAPL and MSFT rows
    back = pd.read_parquet(p29)
    assert sorted(back["ticker"]) == ["AAPL", "MSFT"]


def test_write_partitioned_is_idempotent(tmp_path):
    write_partitioned(_prices_df(), tmp_path, "prices", "trade_date")
    write_partitioned(_prices_df(), tmp_path, "prices", "trade_date")  # rerun same window

    back = pd.read_parquet(bronze_partition_path(tmp_path, "prices", "2026-05-29"))
    assert len(back) == 2  # overwritten, not appended/duplicated


def test_write_partitioned_empty_is_noop(tmp_path):
    assert write_partitioned(pd.DataFrame(), tmp_path, "prices", "trade_date") == []


def test_per_ticker_files_do_not_clobber_each_other(tmp_path):
    # Two tickers loaded separately into the SAME date partition must coexist.
    aapl = pd.DataFrame({"ticker": ["AAPL"], "trade_date": ["2026-05-29"], "close": [312.0]})
    msft = pd.DataFrame({"ticker": ["MSFT"], "trade_date": ["2026-05-29"], "close": [430.1]})
    write_partitioned(aapl, tmp_path, "prices", "trade_date", filename="prices-AAPL.parquet")
    write_partitioned(msft, tmp_path, "prices", "trade_date", filename="prices-MSFT.parquet")

    # Reading the partition directory unions all part-files.
    partition_dir = bronze_partition_path(tmp_path, "prices", "2026-05-29").parent
    back = pd.read_parquet(partition_dir)
    assert sorted(back["ticker"]) == ["AAPL", "MSFT"]


def test_write_snapshot_single_partition(tmp_path):
    df = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "sector": ["Tech", "Tech"]})
    path = write_snapshot(df, tmp_path, "fundamentals", "2026-06-06")
    assert path == bronze_partition_path(tmp_path, "fundamentals", "2026-06-06")
    assert len(pd.read_parquet(path)) == 2


def test_write_snapshot_empty_returns_none(tmp_path):
    assert write_snapshot(pd.DataFrame(), tmp_path, "fundamentals", "2026-06-06") is None
