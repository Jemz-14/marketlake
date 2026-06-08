# ADLS Gen2 storage for the serving layer.
# Holds (a) the Synapse workspace's default filesystem and (b) the gold Parquet
# that Synapse serverless reads. Cheapest viable config: Standard / LRS.
resource "azurerm_storage_account" "lake" {
  name                     = var.storage_account_name
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = data.azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true # hierarchical namespace = ADLS Gen2
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

# Default filesystem the Synapse workspace requires.
resource "azurerm_storage_data_lake_gen2_filesystem" "synapse" {
  name               = "synapse"
  storage_account_id = azurerm_storage_account.lake.id
}

# Filesystem that holds the published gold Parquet (under gold/<table>/).
resource "azurerm_storage_data_lake_gen2_filesystem" "data" {
  name               = "data"
  storage_account_id = azurerm_storage_account.lake.id
}
