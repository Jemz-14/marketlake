# Synapse workspace — we use ONLY its built-in serverless SQL pool (pay-per-query,
# ~$5/TB scanned; our data is tiny). No dedicated SQL pool and no Spark pool are
# created here, so nothing bills hourly.

resource "random_password" "synapse_admin" {
  length      = 28
  special     = false # alphanumeric: meets complexity, avoids shell/conn-string escaping
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
}

resource "azurerm_synapse_workspace" "syn" {
  name                                 = var.synapse_workspace_name
  resource_group_name                  = data.azurerm_resource_group.rg.name
  location                             = data.azurerm_resource_group.rg.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.synapse.id
  sql_administrator_login              = var.synapse_admin_login
  sql_administrator_login_password     = random_password.synapse_admin.result
  public_network_access_enabled        = true

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# Let the serverless SQL pool read the gold Parquet via the workspace's managed
# identity (no keys/SAS in the SQL). Reader is enough for query-only access.
resource "azurerm_role_assignment" "synapse_storage" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_synapse_workspace.syn.identity[0].principal_id
}

# Firewall: your current IP (for running DDL / Power BI) + Azure services.
resource "azurerm_synapse_firewall_rule" "client" {
  name                 = "allow-client-ip"
  synapse_workspace_id = azurerm_synapse_workspace.syn.id
  start_ip_address     = chomp(data.http.my_ip.response_body)
  end_ip_address       = chomp(data.http.my_ip.response_body)
}

resource "azurerm_synapse_firewall_rule" "azure_services" {
  name                 = "AllowAllWindowsAzureIps"
  synapse_workspace_id = azurerm_synapse_workspace.syn.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}
