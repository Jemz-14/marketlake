# Cost report

**Goal:** build the full platform on Azure for **well under $100 AUD**, on a
fresh-graduate budget (~$250 credit). Achieved by choosing serverless,
pay-per-use, and auto-pausing services everywhere and tearing the environment
down between work sessions.

## Deployed resources

| Resource | SKU / mode | Billing model | Est. cost (dev period) |
|---|---|---|---|
| Azure SQL Database (`marketlake`) | `GP_S_Gen5_1` serverless, auto-pause 1h, max 1 vCore, 2 GB | per **active** vCore-second; **$0 compute when paused** + ~$0.17/GB-month storage | **~$5–20** |
| SQL logical server | — | free | $0 |
| ADLS Gen2 | Standard, **LRS** | per GB stored + per-10k operations; data is a few MB | **< $1** |
| Synapse workspace | serverless SQL only — **no dedicated pool, no Spark pool** | workspace **free at rest**; serverless ~$5/TB scanned (our scans are KB–MB) | **< $1** |
| GitHub Actions CI | hosted runners | free tier | $0 |
| Power BI Desktop | authoring | free | $0 |

**Estimated total for the dev period: well under $30 AUD.**

## How cost was controlled

- **Serverless + auto-pause everywhere.** The SQL warehouse auto-pauses after 1h
  idle, so it bills compute only while actually running queries. Synapse uses the
  **serverless** SQL pool (pay-per-query), never a dedicated pool.
- **No always-on compute.** No dedicated SQL pool, no Spark cluster, no VM —
  nothing that bills by the hour while idle. (Verified: `terraform plan` never
  shows an hourly-billed resource.)
- **Cheapest viable storage.** ADLS and the SQL database use **locally-redundant
  storage (LRS)** rather than geo-redundant; tiny data volumes.
- **Tear down between sessions.** `terraform destroy` removes the whole
  environment in one command; `terraform apply` rebuilds it in minutes.
- **Least-privilege networking** (firewall scoped to a single IP) — no
  accidental public exposure to clean up.

## Levers if the data grew 1000×

- Move bronze/silver to ADLS Parquet and lean harder on Synapse serverless
  (scales by data scanned, not by a provisioned cluster).
- Partition the lake by date so queries prune to the relevant files.
- Reserve capacity / commit tiers only once usage is steady and predictable.
