# Runbook — deploy, operate, tear down

## Prerequisites (one-time)
- Azure CLI (`az login`), Terraform ≥ 1.5, Python 3.11, Docker (optional).
- **Microsoft ODBC Driver 18 for SQL Server** (the loader, publish job, and dbt
  connect through it).
- `pip install -r ingestion/requirements.txt -r ingestion/requirements-warehouse.txt -r serving/requirements.txt`
- `dbt/.venv` with `dbt-sqlserver` (see `dbt/README.md`).

## Deploy (cold → fully serving)
```powershell
# 1. Provision all cloud infra (Azure SQL + ADLS + Synapse serverless)
cd infra ; terraform init ; terraform apply ; cd ..
Copy-Item .env.example .env   # fill SQL + storage + synapse values (see `terraform output`)

# 2. Ingest -> local bronze lake
cd ingestion ; python extract.py ; cd ..

# 3. Land bronze in Azure SQL
cd ingestion ; python load_bronze.py ; cd ..

# 4. Build + test silver & gold
. .\scripts\load-env.ps1
cd dbt ; .\.venv\Scripts\dbt.exe build --profiles-dir . ; cd ..

# 5. Publish gold -> ADLS + build Synapse serverless views
cd serving ; python publish_gold.py ; python setup_synapse.py ; cd ..

# 6. (Power BI) open docs/marketlake_dashboard.pbix  (see docs/powerbi_guide.md)
```
Retrieve secrets for `.env` with `cd infra ; terraform output -raw sql_admin_password`
(and `storage_account_key`, `synapse_admin_password`).

## Daily / incremental refresh
`extract.py` and `load_bronze.py` are watermark-incremental and idempotent;
`dbt build` and `publish_gold.py` / `setup_synapse.py` are idempotent. Re-run
steps 2→5 to bring everything current.

## Tear down (stop all spend)
```powershell
cd infra ; terraform destroy
```
Removes the SQL DB, ADLS, and Synapse workspace. Re-`apply` anytime to rebuild.
(Between sessions you can also just let the SQL DB auto-pause — it bills ~$0 idle.)

## Operational gotchas
- **Warehouse auto-pause:** the serverless SQL DB pauses after ~1h idle; the
  first connection while it resumes can time out (~30–60 s). The loader and
  publish job retry automatically; for dbt, just re-run.
- **Dynamic public IP:** the SQL and Synapse firewalls allow your current IP
  (`data.http.my_ip`). When your ISP changes it, connections are refused —
  fix with `cd infra ; terraform apply` (re-reads and updates both rules).
- **Synapse first-run lock:** a freshly-created workspace briefly locks the
  system `model` db (error 1807); `setup_synapse.py` retries through it.
- **Power BI auth:** connect on the **Database** (SQL login) tab, not Windows.
