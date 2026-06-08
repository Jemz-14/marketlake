output "sql_server_fqdn" {
  description = "Fully-qualified server name — used in dbt's connection."
  value       = azurerm_mssql_server.sql.fully_qualified_domain_name
}

output "sql_database_name" {
  description = "Warehouse database name."
  value       = azurerm_mssql_database.db.name
}

output "sql_admin_login" {
  description = "SQL admin login."
  value       = var.sql_admin_login
}

output "sql_admin_password" {
  description = "Generated SQL admin password. Read with: terraform output -raw sql_admin_password"
  value       = random_password.sql_admin.result
  sensitive   = true
}

# --- Serving layer (Phase 3) ---

output "storage_account_name" {
  description = "ADLS Gen2 account holding the gold Parquet."
  value       = azurerm_storage_account.lake.name
}

output "storage_dfs_endpoint" {
  description = "ADLS Gen2 DFS endpoint (https://<acct>.dfs.core.windows.net)."
  value       = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "storage_data_filesystem" {
  description = "Filesystem (container) the gold Parquet is published to."
  value       = azurerm_storage_data_lake_gen2_filesystem.data.name
}

output "storage_account_key" {
  description = "Storage account key for the export job. Read with: terraform output -raw storage_account_key"
  value       = azurerm_storage_account.lake.primary_access_key
  sensitive   = true
}

output "synapse_serverless_endpoint" {
  description = "Synapse serverless SQL endpoint (use as the server in dbt/Power BI/pyodbc)."
  value       = azurerm_synapse_workspace.syn.connectivity_endpoints["sqlOnDemand"]
}

output "synapse_admin_login" {
  description = "Synapse SQL admin login."
  value       = var.synapse_admin_login
}

output "synapse_admin_password" {
  description = "Generated Synapse admin password. Read with: terraform output -raw synapse_admin_password"
  value       = random_password.synapse_admin.result
  sensitive   = true
}
