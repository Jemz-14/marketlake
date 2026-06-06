# MarketLake infrastructure (Phase 2: the warehouse)
# Provisions a serverless, auto-pausing Azure SQL Database to act as the dbt
# warehouse. Everything here is cost-guarded: it pauses after 1h idle (≈ $0
# compute when not in use) and uses the cheapest viable storage.

terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

locals {
  tags = {
    project = "marketlake"
    env     = "dev"
    managed = "terraform"
  }
}

# The resource group you created in Phase 0 — read it, don't manage it here.
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

# Your current public IP, so the SQL firewall can be opened just for you.
data "http" "my_ip" {
  url = "https://api.ipify.org"
}

# Strong random admin password — never written to source, only to local state.
resource "random_password" "sql_admin" {
  length           = 24
  min_upper        = 1
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
  override_special = "!#%*-_=+" # connection-string-safe symbols only
}

# Logical SQL server (the host that the database lives on).
resource "azurerm_mssql_server" "sql" {
  name                         = var.sql_server_name
  resource_group_name          = data.azurerm_resource_group.rg.name
  location                     = data.azurerm_resource_group.rg.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_login
  administrator_login_password = random_password.sql_admin.result
  minimum_tls_version          = "1.2"
  tags                         = local.tags
}

# The warehouse: General Purpose, Serverless, Gen5, up to 1 vCore.
resource "azurerm_mssql_database" "db" {
  name                        = var.sql_database_name
  server_id                   = azurerm_mssql_server.sql.id
  sku_name                    = "GP_S_Gen5_1"
  min_capacity                = 0.5
  auto_pause_delay_in_minutes = 60 # pause after 1h idle (the minimum)
  max_size_gb                 = 2
  collation                   = "SQL_Latin1_General_CP1_CI_AS"
  storage_account_type        = "Local" # locally-redundant = cheapest
  zone_redundant              = false
  tags                        = local.tags
}

# Firewall: allow only your current public IP to reach the server.
resource "azurerm_mssql_firewall_rule" "client" {
  name             = "allow-client-ip"
  server_id        = azurerm_mssql_server.sql.id
  start_ip_address = chomp(data.http.my_ip.response_body)
  end_ip_address   = chomp(data.http.my_ip.response_body)
}
