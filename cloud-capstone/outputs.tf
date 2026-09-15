# ──────────────────────────────────────────────
# Resource Group
# ──────────────────────────────────────────────
output "resource_group_name" {
  description = "Resource group containing all pharmacy resources"
  value       = azurerm_resource_group.rg.name
}

# ──────────────────────────────────────────────
# Network
# ──────────────────────────────────────────────
output "vnet_name" {
  description = "Virtual Network name"
  value       = azurerm_virtual_network.vnet.name
}

# ──────────────────────────────────────────────
# Application Gateway — Primary Application URL
# ──────────────────────────────────────────────
output "application_url" {
  description = "Primary application URL via Application Gateway (pharmacy frontend)"
  value       = "http://${azurerm_public_ip.appgw_pip.ip_address}"
}

output "appgw_public_ip" {
  description = "Application Gateway frontend public IP"
  value       = azurerm_public_ip.appgw_pip.ip_address
}

# ──────────────────────────────────────────────
# Backend VMs
# ──────────────────────────────────────────────
output "vm_public_ips" {
  description = "Public IPs of the backend VMs"
  value       = [for pip in azurerm_public_ip.vm_pip : pip.ip_address]
}

# ──────────────────────────────────────────────
# Azure SQL
# ──────────────────────────────────────────────
output "sql_server_fqdn" {
  description = "Fully qualified domain name of the SQL Server"
  value       = azurerm_mssql_server.sql.fully_qualified_domain_name
}

output "sql_database_name" {
  description = "Inventory database name"
  value       = azurerm_mssql_database.inventorydb.name
}

# ──────────────────────────────────────────────
# Blob Storage
# ──────────────────────────────────────────────
output "storage_account_name" {
  description = "Storage account name for replenishment reports"
  value       = azurerm_storage_account.storage.name
}

output "storage_container_name" {
  description = "Blob container for replenishment reports"
  value       = azurerm_storage_container.reports.name
}

# ──────────────────────────────────────────────
# Service Bus — NEW
# ──────────────────────────────────────────────
output "service_bus_namespace" {
  description = "Service Bus namespace name"
  value       = azurerm_servicebus_namespace.sb.name
}

output "service_bus_queue_name" {
  description = "Service Bus queue name for replenishment messages"
  value       = azurerm_servicebus_queue.replenishment_queue.name
}
