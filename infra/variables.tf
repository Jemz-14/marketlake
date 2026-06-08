variable "subscription_id" {
  description = "Azure subscription ID to deploy into."
  type        = string
}

variable "resource_group_name" {
  description = "Existing resource group created in Phase 0."
  type        = string
}

variable "sql_server_name" {
  description = "Globally-unique name for the logical SQL server (lowercase, 3-63 chars, letters/digits/hyphens)."
  type        = string
}

variable "sql_database_name" {
  description = "Database (warehouse) name."
  type        = string
  default     = "marketlake"
}

variable "sql_admin_login" {
  description = "SQL administrator login name."
  type        = string
  default     = "marketlakeadmin"
}

variable "storage_account_name" {
  description = "Globally-unique ADLS Gen2 account name (3-24 chars, lowercase letters/digits only)."
  type        = string
}

variable "synapse_workspace_name" {
  description = "Globally-unique Synapse workspace name (1-50 chars, lowercase letters/digits)."
  type        = string
}

variable "synapse_admin_login" {
  description = "Synapse SQL administrator login name."
  type        = string
  default     = "synapseadmin"
}
