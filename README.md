# MarketLake — Cloud-Native Market Data Platform on Azure

A medallion-architecture data platform that ingests multi-source market data,
lands it in a lake, and models it into a tested star schema on Azure SQL with
dbt. Built incrementally as a portfolio project demonstrating the patterns
hiring managers screen for: layered storage, incremental loading, dimensional
modelling, data quality, infrastructure-as-code, and containerisation.

**Stack:** Python · Docker · Azure SQL Database (serverless) · dbt
(`dbt-sqlserver`) · Terraform · GitHub

---

## Architecture

```
 SOURCES                INGEST (Python)        LAKE (local / ADLS)      WAREHOUSE (Azure SQL)
 ┌───────────┐                              ┌────────────────────┐
 │ yfinance  │ prices ─┐                    │ bronze/  (raw       │   bronze.*   (raw landed)
 │ yfinance  │ fundam. ─┼─► extract.py ────►│   Parquet, by date) │      │  dbt staging (views)
 │ Frankfurt.│ fx     ─┘   (watermark        └────────────────────┘      ▼
 └───────────┘             incremental)               │ load_bronze.py   silver.stg_*  (typed/clean)
                                                       └────────────────►     │  dbt marts (tables)
                                                                               ▼
                                                                          gold.*  (star schema +
                                                                                   indicators)
 Infra (Azure SQL) provisioned by Terraform.  dbt builds + tests silver & gold.
```

**Medallion layers**
- **bronze** — raw, immutable, partitioned Parquet (`bronze/<source>/date=YYYY-MM-DD/`), then landed 1:1 into the `bronze` SQL schema.
- **silver** — typed, deduplicated, conformed views (`stg_prices`, `stg_fx`, `stg_fundamentals`).
- **gold** — a dimensional star schema plus technical indicators.

### Gold star schema

```
   dim_date ──┐                         ┌── dim_security ──► dim_sector
              ├──< fact_daily_price >──┤
              └────────────────────────┘
                fact_price_indicators (returns, SMA, RSI, EMA, MACD)
```

- `fact_daily_price` — grain: one row per security per day; OHLCV + **AUD-normalised close** (as-of FX join).
- `fact_price_indicators` — daily return, SMA 20/50, RSI-14, EMA 12/26, MACD.
- `dim_security`, `dim_sector`, `dim_date` — conformed dimensions with surrogate keys.
- Referential integrity enforced by dbt `relationships` tests (fact→dims, dim_security→dim_sector).

---

## Repository layout

| Path | What |
|---|---|
| [`ingestion/`](ingestion/README.md) | Python extractors → bronze Parquet (watermark incremental), the bronze→SQL loader, and the Docker image. |
| [`infra/`](infra/README.md) | Terraform for the Azure SQL warehouse, ADLS Gen2, and the Synapse serverless workspace. |
| [`dbt/`](dbt/README.md) | dbt project: silver staging + gold marts, tests, docs. |
| `serving/` | Publish gold → ADLS Parquet and build Synapse serverless views over it. |
| `scripts/` | `load-env.ps1` — load `.env` creds into a PowerShell session. |
| `docs/` | Analytical SQL queries, the Power BI guide + `.pbix`, architecture notes. |

---

## Quickstart

```powershell
# 0. Python env + warehouse credentials
.\.venv\Scripts\Activate.ps1
pip install -r ingestion\requirements.txt -r ingestion\requirements-warehouse.txt -r serving\requirements.txt
Copy-Item .env.example .env          # then fill in (see infra/ for the password)

# 1. Ingest sources -> local bronze lake (incremental, idempotent)
cd ingestion ; python extract.py ; cd ..

# 2. Provision the cloud infra (Azure SQL warehouse, ADLS Gen2, Synapse serverless)
cd infra ; terraform init ; terraform apply ; cd ..

# 3. Load bronze Parquet -> Azure SQL bronze schema
cd ingestion ; python load_bronze.py ; cd ..

# 4. Build + test the silver & gold models
. .\scripts\load-env.ps1
cd dbt ; .\.venv\Scripts\dbt.exe build --profiles-dir . ; cd ..

# 5. Publish gold -> ADLS Parquet, then build the Synapse serverless views
cd serving ; python publish_gold.py ; python setup_synapse.py ; cd ..

# 6. (Optional) Open docs/marketlake_dashboard.pbix in Power BI Desktop
#    (connect to the Synapse serverless endpoint; see docs/powerbi_guide.md)
```

Per-component details live in the linked READMEs above.

### Containerised ingestion (optional)

```powershell
cd ingestion
docker build -t marketlake-ingest .
docker run --rm -v "${PWD}\_lake:/data" marketlake-ingest
```

---

## Data quality

Every dbt build runs the test suite (39 tests): `not_null`, `unique`,
`accepted_values`, composite-key uniqueness, `relationships`, and a value-range
check on RSI. A failing test fails the build.

```powershell
cd dbt ; .\.venv\Scripts\dbt.exe test --profiles-dir .
```

View the model documentation and lineage graph:

```powershell
cd dbt ; .\.venv\Scripts\dbt.exe docs generate --profiles-dir . ; .\.venv\Scripts\dbt.exe docs serve --profiles-dir .
```

---

## Cost control

The only billable resource is a **serverless Azure SQL Database** that
**auto-pauses after 1h idle** (≈ $0 compute when asleep). Tear it down between
sessions with `cd infra ; terraform destroy`. Target total spend: well under
$100 AUD.

---

## Status

- ✅ **Phase 1 — Ingestion → Bronze:** Python extractors (prices, fundamentals, FX), watermark-incremental, partitioned Parquet, Dockerised.
- ✅ **Phase 2 — Transform → Silver & Gold:** Terraform warehouse, bronze loader, dbt silver staging + gold star schema + indicators, tested.
- ✅ **Phase 3 — Serving:** gold published to ADLS Gen2 Parquet; Synapse serverless external views (managed identity); analytical SQL queries; Power BI dashboard.
- ⏭️ Phase 4 — Production-readiness (Terraform CI/CD with GitHub Actions, data-quality gates, observability).
