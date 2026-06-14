# MarketLake — Microsoft Fabric medallion notebook (PySpark + Delta Lake)
# -----------------------------------------------------------------------------
# Reads the bronze Parquet from the Lakehouse Files, builds silver (typed/deduped)
# and the gold star schema + technical indicators, and writes them as Delta
# tables in the Lakehouse.
#
# HOW TO RUN IN FABRIC:
#   1. Create a Notebook in the MarketLake workspace; attach `marketlake_lh` as
#      its default Lakehouse (Explorer panel -> Add -> Existing Lakehouse).
#   2. Paste this whole file into a cell (or split on the "# === Cell" markers)
#      and Run all. Tables appear under the Lakehouse "Tables" section.
#
# The same file also runs locally (creates its own Spark+Delta session) for
# testing -- see fabric/run_local.py.
# -----------------------------------------------------------------------------

# === Cell 1: Spark session + paths =========================================
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

try:
    spark  # noqa: F821  -- provided automatically inside a Fabric notebook
    BRONZE = "Files/bronze"
    print("Running inside Fabric.")
except NameError:
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession
    _builder = (
        SparkSession.builder.appName("marketlake-fabric-local")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        # keep local scratch (managed tables + Derby metastore) out of the repo
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
        .config("spark.driver.extraJavaOptions", "-Dderby.system.home=/tmp")
    )
    spark = configure_spark_with_delta_pip(_builder).getOrCreate()
    BRONZE = "fabric/bronze_upload"
    print("Running locally.")


def surrogate_key(*cols):
    """MD5 surrogate key over the given columns (cast/coalesced to string)."""
    parts = [F.coalesce(F.col(c).cast("string"), F.lit("")) for c in cols]
    return F.md5(F.concat_ws("||", *parts))


# === Cell 2: read bronze ====================================================
prices_raw = spark.read.parquet(f"{BRONZE}/prices.parquet")
fx_raw = spark.read.parquet(f"{BRONZE}/fx.parquet")
fund_raw = spark.read.parquet(f"{BRONZE}/fundamentals.parquet")

# === Cell 3: silver — typed, deduped =======================================
stg_prices = (
    prices_raw
    .withColumn("trade_date", F.to_date("trade_date"))
    .withColumn("_rn", F.row_number().over(
        Window.partitionBy("ticker", "trade_date").orderBy(F.col("_ingested_at").desc())))
    .filter(F.col("_rn") == 1)
    .select(
        "ticker", "trade_date",
        F.col("open").alias("open_price"),
        F.col("high").alias("high_price"),
        F.col("low").alias("low_price"),
        F.col("close").alias("close_price"),
        F.col("adj_close").alias("adj_close_price"),
        "volume",
    )
)

stg_fx = (
    fx_raw
    .withColumn("rate_date", F.to_date("rate_date"))
    .withColumn("_rn", F.row_number().over(
        Window.partitionBy("rate_date", "base_currency", "quote_currency")
        .orderBy(F.col("_ingested_at").desc())))
    .filter(F.col("_rn") == 1)
    .select("rate_date", "base_currency", "quote_currency", "rate")
)

stg_fund = (
    fund_raw
    .withColumn("snapshot_date", F.to_date("snapshot_date"))
    .withColumn("_rn", F.row_number().over(
        Window.partitionBy("ticker").orderBy(F.col("snapshot_date").desc(),
                                             F.col("_ingested_at").desc())))
    .filter(F.col("_rn") == 1)
    .select("ticker", F.col("long_name").alias("company_name"), "sector",
            "industry", "market_cap", "currency", "exchange", "country", "quote_type")
)

# === Cell 4: gold dimensions ===============================================
dim_security = (
    stg_prices.select("ticker").distinct()
    .join(stg_fund, "ticker", "left")
    .withColumn("sector", F.coalesce(F.col("sector"), F.lit("Unknown")))
    .withColumn("security_key", surrogate_key("ticker"))
    .withColumn("sector_key", surrogate_key("sector"))
    .select("security_key", "ticker", "company_name", "sector", "sector_key",
            "industry", "currency", "exchange", "country", "quote_type", "market_cap")
)

dim_sector = (
    dim_security.select("sector").distinct()
    .withColumn("sector_key", surrogate_key("sector"))
    .select("sector_key", "sector")
)

_b = stg_prices.select(F.min("trade_date").alias("mn"), F.max("trade_date").alias("mx")).collect()[0]
_start, _end = f"{_b['mn'].year}-01-01", f"{_b['mx'].year + 1}-12-31"
dim_date = (
    spark.sql(f"SELECT explode(sequence(to_date('{_start}'), to_date('{_end}'), "
              f"interval 1 day)) AS full_date")
    .withColumn("date_key", F.date_format("full_date", "yyyyMMdd").cast("int"))
    .withColumn("year", F.year("full_date"))
    .withColumn("quarter", F.quarter("full_date"))
    .withColumn("month", F.month("full_date"))
    .withColumn("month_name", F.date_format("full_date", "MMMM"))
    .withColumn("day_of_month", F.dayofmonth("full_date"))
    .withColumn("day_name", F.date_format("full_date", "EEEE"))
    # dayofweek is 1=Sun..7=Sat (numeric -> language-independent)
    .withColumn("is_weekend", F.when(F.dayofweek("full_date").isin(1, 7), 1).otherwise(0))
    .select("date_key", "full_date", "year", "quarter", "month", "month_name",
            "day_of_month", "day_name", "is_weekend")
)

# === Cell 5: fact_daily_price (AUD-normalised via as-of FX join) ============
_priced = stg_prices.join(dim_security.select("ticker", "currency"), "ticker", "left")
_asof = (
    _priced.join(
        stg_fx,
        (stg_fx.quote_currency == _priced.currency) & (stg_fx.rate_date <= _priced.trade_date),
        "left")
    .withColumn("_rn", F.row_number().over(
        Window.partitionBy("ticker", "trade_date").orderBy(F.col("rate_date").desc())))
    .filter(F.col("_rn") == 1)
)

fact_daily_price = (
    _asof
    .withColumn("daily_price_key", surrogate_key("ticker", "trade_date"))
    .withColumn("security_key", surrogate_key("ticker"))
    .withColumn("date_key", F.date_format("trade_date", "yyyyMMdd").cast("int"))
    .withColumn("aud_fx_rate", F.col("rate"))
    .withColumn("close_price_aud",
                F.when(F.col("currency") == "AUD", F.col("close_price"))
                 .when(F.col("rate").isNotNull(), F.col("close_price") / F.col("rate")))
    .select("daily_price_key", "security_key", "date_key", "ticker", "trade_date",
            "open_price", "high_price", "low_price", "close_price", "adj_close_price",
            "volume", "currency", "aud_fx_rate", "close_price_aud")
)

# === Cell 6: fact_price_indicators (Spark + pandas; true recursive EMA) =====
_ind_schema = T.StructType([
    T.StructField("security_key", T.StringType()),
    T.StructField("date_key", T.IntegerType()),
    T.StructField("daily_return", T.DoubleType()),
    T.StructField("sma_20", T.DoubleType()),
    T.StructField("sma_50", T.DoubleType()),
    T.StructField("rsi_14", T.DoubleType()),
    T.StructField("ema_12", T.DoubleType()),
    T.StructField("ema_26", T.DoubleType()),
    T.StructField("macd_line", T.DoubleType()),
    T.StructField("macd_signal", T.DoubleType()),
    T.StructField("macd_histogram", T.DoubleType()),
])


def _indicators(pdf):
    # One security's rows as a pandas frame -> compute indicators with pandas.
    pdf = pdf.sort_values("date_key")
    close = pdf["close_price"]
    out = pdf[["security_key", "date_key"]].copy()
    out["daily_return"] = close.pct_change()
    out["sma_20"] = close.rolling(20).mean()
    out["sma_50"] = close.rolling(50).mean()
    diff = close.diff()
    avg_gain = diff.clip(lower=0).rolling(14).mean()
    avg_loss = (-diff.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + avg_gain / avg_loss)
    rsi[avg_loss == 0] = 100
    out["rsi_14"] = rsi
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    out["ema_12"], out["ema_26"] = ema_12, ema_26
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()
    out["macd_line"], out["macd_signal"], out["macd_histogram"] = macd, signal, macd - signal
    return out


_ind = (
    fact_daily_price.select("security_key", "date_key", "close_price")
    .groupBy("security_key").applyInPandas(_indicators, schema=_ind_schema)
)
fact_price_indicators = _ind.join(
    fact_daily_price.select("security_key", "date_key", "ticker", "trade_date", "close_price"),
    ["security_key", "date_key"])

# === Cell 7: write Delta tables to the Lakehouse ===========================
_tables = {
    "dim_date": dim_date,
    "dim_security": dim_security,
    "dim_sector": dim_sector,
    "fact_daily_price": fact_daily_price,
    "fact_price_indicators": fact_price_indicators,
}
for _name, _df in _tables.items():
    _df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(_name)
    print(f"wrote {_name}: {_df.count()} rows")

print("Done — gold Delta tables are in the Lakehouse.")
