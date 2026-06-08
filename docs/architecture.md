# Architecture

MarketLake is a medallion-architecture data platform on Azure. Sources are
ingested to a partitioned bronze lake, landed in Azure SQL, modelled into a
tested gold star schema with dbt, then served via Synapse serverless and
Power BI. Everything is provisioned with Terraform and gated by GitHub Actions.

```mermaid
flowchart LR
  subgraph Sources
    Y[yfinance prices]
    F[yfinance fundamentals]
    X[Frankfurter FX]
  end

  subgraph Ingest [Ingest - Python]
    E[extract.py\nwatermark incremental]
    L[load_bronze.py]
  end

  subgraph Lake [Bronze lake]
    B[(Parquet\nbronze/source/date=.../)]
  end

  subgraph Warehouse [Azure SQL]
    BR[bronze.*]
    SI[silver.stg_*]
    GO[gold.* star schema\n+ indicators]
  end

  subgraph Serve
    ADLS[(ADLS Gen2\ngold Parquet)]
    SYN[Synapse serverless\nexternal views]
    PBI[Power BI dashboard]
  end

  Y & F & X --> E --> B --> L --> BR
  BR -->|dbt staging| SI -->|dbt marts| GO
  GO -->|publish_gold.py| ADLS --> SYN --> PBI
  GO -.direct.-> PBI
```

## Layers

- **Bronze** — raw, immutable, partitioned Parquet (`bronze/<source>/date=YYYY-MM-DD/`),
  then mirrored 1:1 into the SQL `bronze` schema.
- **Silver** — dbt staging *views*: typed, deduplicated, conformed.
- **Gold** — dbt marts *tables*: a star schema (`fact_daily_price`,
  `fact_price_indicators`, `dim_security`, `dim_sector`, `dim_date`) with
  surrogate keys and `relationships` tests, plus an AUD-normalised close and
  technical indicators.

## Cross-cutting

- **IaC:** Terraform provisions the SQL warehouse, ADLS Gen2, and the Synapse
  workspace — one `apply` / one `destroy`.
- **CI:** GitHub Actions runs ruff + pytest, `terraform fmt`/`validate`, and
  `dbt deps`/`parse` on every PR.
- **Data quality:** dbt tests (`not_null`, `unique`, `accepted_values`,
  `relationships`, range checks) gate every `dbt build`.
- **Cost:** serverless + auto-pause throughout; see [cost_report.md](cost_report.md).

## Key design decisions

- **Multiple sources → a real star schema** (facts + conformed dimensions),
  rather than a single flat price table.
- **Medallion layering** so every transform is explicit, testable, re-runnable.
- **Watermark incremental loading** — only new dates are pulled; runs are idempotent.
- **Synapse serverless over Parquet** demonstrates the Synapse skill at
  pay-per-query cost (no dedicated pool).
