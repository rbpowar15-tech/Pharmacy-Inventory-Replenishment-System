# ──────────────────────────────────────────────
# General
# ──────────────────────────────────────────────
variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "rg-pharmacy"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "India South Central"
}

variable "project_tags" {
  description = "Tags applied to every resource"
  type        = map(string)
  default = {
    Project     = "PharmacyInventory"
    Environment = "Training"
    Team        = "Team3"
  }
}

# ──────────────────────────────────────────────
# Networking
# ──────────────────────────────────────────────
variable "vnet_address_space" {
  description = "Address space for the VNet"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "web_subnet_prefix" {
  description = "CIDR for the web/API subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "appgw_subnet_prefix" {
  description = "CIDR for the Application Gateway subnet"
  type        = string
  default     = "10.0.2.0/24"
}

# ──────────────────────────────────────────────
# Virtual Machines
# ──────────────────────────────────────────────
variable "vm_size" {
  description = "Size of the backend VMs"
  type        = string
  default     = "Standard_B1s"
}

variable "admin_username" {
  description = "Admin username for VMs"
  type        = string
  default     = "azureuser"
}

variable "admin_password" {
  description = "Admin password for VMs (use a strong value)"
  type        = string
  sensitive   = true
}

variable "vm_count" {
  description = "Number of backend VMs"
  type        = number
  default     = 2
}

# ──────────────────────────────────────────────
# Azure SQL
# ──────────────────────────────────────────────
variable "sql_admin_login" {
  description = "SQL Server administrator login"
  type        = string
  default     = "sqladmin"
}

variable "sql_admin_password" {
  description = "SQL Server administrator password"
  type        = string
  sensitive   = true
}

variable "allowed_ip" {
  description = "Your public IP for SQL firewall rule (for training)"
  type        = string
  default     = "0.0.0.0"
}

# ──────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────
variable "storage_account_name" {
  description = "Globally unique storage account name (lowercase, no hyphens)"
  type        = string
  default     = "stpharmacyinv"
}
