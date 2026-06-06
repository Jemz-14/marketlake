# MarketLake — Infrastructure (Terraform)

Provisions the Phase 2 warehouse: a **serverless, auto-pausing Azure SQL
Database** inside the resource group you created in Phase 0.

| Resource | Setting | Why |
|---|---|---|
| `azurerm_mssql_database` | `GP_S_Gen5_1`, `min_capacity = 0.5`, `auto_pause_delay = 60`, `storage = Local` | Cheapest viable warehouse: pauses after 1h idle (≈ $0 compute), bills only storage (~pennies) when asleep. |
| `azurerm_mssql_firewall_rule` | your current public IP only | Least-privilege network access for local dbt runs. |
| `random_password` | 24-char admin password | Kept out of source; lives only in local state (gitignored). |

## Deploy

```powershell
az login                       # Terraform authenticates via your az session
cd infra
Copy-Item terraform.tfvars.example terraform.tfvars   # then edit the values
terraform init
terraform plan                 # review — confirm nothing bills hourly
terraform apply
```

Retrieve the connection details for dbt:

```powershell
terraform output sql_server_fqdn
terraform output sql_database_name
terraform output -raw sql_admin_password    # sensitive — don't paste into chat
```

## Cost control

- The database auto-pauses after 1 hour idle. To be certain you're not billed
  between sessions, you can also tear it down and re-create later:
  ```powershell
  terraform destroy
  ```
- `terraform plan` should never show a dedicated SQL pool, a Spark cluster, or
  any always-on compute. If it does, stop and ask.
