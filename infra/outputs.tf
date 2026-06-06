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
