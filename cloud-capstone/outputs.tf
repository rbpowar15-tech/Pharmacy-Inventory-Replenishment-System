output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "vnet_name" {
  value = azurerm_virtual_network.vnet.name
}

output "vm_public_ips" {
  description = "Public IPs of the backend VMs"
  value       = [for pip in azurerm_public_ip.vm_pip : pip.ip_address]
}

output "appgw_public_ip" {
  description = "Application Gateway frontend public IP"
  value       = azurerm_public_ip.appgw_pip.ip_address
}

output "sql_server_fqdn" {
  description = "Fully qualified domain name of the SQL Server"
  value       = azurerm_mssql_server.sql.fully_qualified_domain_name
}

output "sql_database_name" {
  value = azurerm_mssql_database.inventorydb.name
}

output "storage_account_name" {
  value = azurerm_storage_account.storage.name
}

output "storage_container_name" {
  value = azurerm_storage_container.reports.name
}
