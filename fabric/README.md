# Fabric / PySpark edition (v3)

Recreates the gold layer with **PySpark + Delta Lake**, targeting a **Microsoft
Fabric Lakehouse (OneLake)** — the same medallion model as the dbt/Azure SQL
build, expressed in Spark.

> Status: the notebook is **tested end-to-end** (see below) and Fabric-ready.
> It was authored against Fabric but not deployed to a live workspace (Fabric
> trial access was gated on the available tenants).

## What's here
- **`consolidate_bronze.py`** — collapses the partitioned local bronze lake into
  one Parquet file per source (`prices` / `fx` / `fundamentals`) for upload to
  the Lakehouse `Files/bronze/`.
- **`medallion_notebook.py`** — the PySpark notebook: bronze Parquet → silver
  (typed/deduped) → gold star schema (`fact_daily_price` with AUD-normalised
  as-of FX join, `dim_security/sector/date`) → technical indicators → **Delta
  tables**. Indicators use `applyInPandas`, so each security is computed in
  pandas — giving a *true recursive* EMA/MACD via `ewm()`.

## Run in Fabric
1. Lakehouse → `Files` → create `bronze/` and upload the 3 files from
   `bronze_upload/` (generate them with `python fabric/consolidate_bronze.py`).
2. New **Notebook**, attach the Lakehouse as default, paste
   `medallion_notebook.py`, **Run all**.
3. The Delta tables appear under the Lakehouse **Tables**, ready for Power BI.

## How it was validated
Run end-to-end in a Linux **Spark 3.5 + Delta 3.2** container (the notebook's
local branch creates its own Spark/Delta session):

```powershell
docker run --rm --mount "type=bind,source=<repo-path>,target=/work" python:3.11-slim-bookworm `
  bash -c "cd /work && apt-get update -qq && apt-get install -y -qq openjdk-17-jre-headless && \
           pip install -q pyspark==3.5.3 delta-spark==3.2.0 pandas pyarrow && \
           python fabric/medallion_notebook.py"
```

Output matched the dbt gold layer exactly: `dim_date` 730, `dim_security` 5,
`dim_sector` 4, `fact_daily_price` 340, `fact_price_indicators` 340.
