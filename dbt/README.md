# MarketLake — dbt (silver + gold)

Transforms the raw `bronze.*` tables in Azure SQL into a cleaned **silver**
layer (staging views) and a modelled **gold** star schema (marts), with tests
and docs.

- **Adapter:** `dbt-sqlserver` (installed in `dbt/.venv`).
- **Credentials:** read from environment variables via `profiles.yml` (no
  secrets committed). Load them from the repo-root `.env` first.
- **Schemas:** `staging/` → `silver`, `marts/` → `gold` (see
  `macros/generate_schema_name.sql`).

## One-time setup

```powershell
# from the repo root: load warehouse creds into the session
. .\scripts\load-env.ps1

cd dbt
.\.venv\Scripts\Activate.ps1     # or call .\.venv\Scripts\dbt.exe directly
dbt deps --profiles-dir .         # install dbt_utils
dbt debug --profiles-dir .        # verify the connection to Azure SQL
```

## Everyday commands (run from the `dbt/` directory)

```powershell
dbt run   --profiles-dir .        # build silver + gold
dbt test  --profiles-dir .        # run data-quality tests
dbt build --profiles-dir .        # run + test together
dbt docs generate --profiles-dir . ; dbt docs serve --profiles-dir .
```

> If you get an env_var error, you forgot `. .\scripts\load-env.ps1` in this
> session. The Azure SQL DB auto-pauses after 1h idle; the first command after
> a pause may take ~30s while it resumes.
