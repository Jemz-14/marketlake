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
