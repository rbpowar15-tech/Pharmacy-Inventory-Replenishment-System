# ──────────────────────────────────────────────
# Resource Group
# ──────────────────────────────────────────────
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.project_tags
}

# ──────────────────────────────────────────────
# Random suffix for globally unique names
# ──────────────────────────────────────────────
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

# ══════════════════════════════════════════════
# STEP 1 — Virtual Network & Subnets
# ══════════════════════════════════════════════
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-pharmacy"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = var.vnet_address_space
  tags                = var.project_tags
}

resource "azurerm_subnet" "web" {
  name                 = "snet-web"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.web_subnet_prefix]
}

resource "azurerm_subnet" "appgw" {
  name                 = "snet-appgw"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.appgw_subnet_prefix]
}

# ══════════════════════════════════════════════
# STEP 2 — Network Security Group for Web VMs
# ══════════════════════════════════════════════
resource "azurerm_network_security_group" "web_nsg" {
  name                = "nsg-web"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.project_tags

  security_rule {
    name                       = "Allow-HTTP"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Allow-SSH"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.allowed_ip
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "web_nsg_assoc" {
  subnet_id                 = azurerm_subnet.web.id
  network_security_group_id = azurerm_network_security_group.web_nsg.id
}

# ══════════════════════════════════════════════
# STEP 3 — Two Backend VMs (Inventory API hosts)
# ══════════════════════════════════════════════
resource "azurerm_public_ip" "vm_pip" {
  count               = var.vm_count
  name                = "pip-vm-${count.index + 1}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.project_tags
}

resource "azurerm_network_interface" "vm_nic" {
  count               = var.vm_count
  name                = "nic-vm-${count.index + 1}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.project_tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.web.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm_pip[count.index].id
  }
}

resource "azurerm_linux_virtual_machine" "backend" {
  count               = var.vm_count
  name                = "vm-inventory-${count.index + 1}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  size                = var.vm_size
  admin_username      = var.admin_username
  admin_password      = var.admin_password
  disable_password_authentication = false
  tags                = var.project_tags

  network_interface_ids = [
    azurerm_network_interface.vm_nic[count.index].id
  ]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # Install NGINX on boot so that the App Gateway health probe succeeds
  custom_data = base64encode(<<-CLOUD_INIT
    #!/bin/bash
    apt-get update -y
    apt-get install -y nginx
    echo "<h1>Pharmacy Inventory API — VM $(hostname)</h1>" > /var/www/html/index.html
    systemctl enable nginx
    systemctl start nginx
  CLOUD_INIT
  )
}

# ══════════════════════════════════════════════
# STEP 4 — Application Gateway (Load Balancer)
# ══════════════════════════════════════════════
resource "azurerm_public_ip" "appgw_pip" {
  name                = "pip-appgw"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.project_tags
}

locals {
  appgw_name               = "appgw-pharmacy"
  frontend_ip_config_name  = "appgw-feip"
  frontend_port_name       = "appgw-feport"
  backend_pool_name        = "appgw-bepool"
  http_setting_name        = "appgw-http-setting"
  listener_name            = "appgw-listener"
  request_routing_name     = "appgw-rule"
  probe_name               = "appgw-health-probe"
}

resource "azurerm_application_gateway" "appgw" {
  name                = local.appgw_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.project_tags

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 1
  }

    ssl_policy {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101"
  }

  gateway_ip_configuration {
    name      = "appgw-ip-config"
    subnet_id = azurerm_subnet.appgw.id
  }

  frontend_ip_configuration {
    name                 = local.frontend_ip_config_name
    public_ip_address_id = azurerm_public_ip.appgw_pip.id
  }

  frontend_port {
    name = local.frontend_port_name
    port = 80
  }

  # Backend pool pointing to the two VM private IPs
  backend_address_pool {
    name         = local.backend_pool_name
    ip_addresses = [for nic in azurerm_network_interface.vm_nic : nic.private_ip_address]
  }

  backend_http_settings {
    name                  = local.http_setting_name
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 30
    probe_name            = local.probe_name
  }

  probe {
    name                = local.probe_name
    protocol            = "Http"
    path                = "/"
    host                = "127.0.0.1"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3
  }

  http_listener {
    name                           = local.listener_name
    frontend_ip_configuration_name = local.frontend_ip_config_name
    frontend_port_name             = local.frontend_port_name
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = local.request_routing_name
    priority                   = 1
    rule_type                  = "Basic"
    http_listener_name         = local.listener_name
    backend_address_pool_name  = local.backend_pool_name
    backend_http_settings_name = local.http_setting_name
  }
}

# ══════════════════════════════════════════════
# STEP 5 — Azure SQL Server & Database
# ══════════════════════════════════════════════
resource "azurerm_mssql_server" "sql" {
  name                         = "sql-pharmacy-${random_string.suffix.result}"
  location                     = azurerm_resource_group.rg.location
  resource_group_name          = azurerm_resource_group.rg.name
  version                      = "12.0"
  administrator_login          = var.sql_admin_login
  administrator_login_password = var.sql_admin_password
  tags                         = var.project_tags
}

resource "azurerm_mssql_database" "inventorydb" {
  name      = "inventorydb"
  server_id = azurerm_mssql_server.sql.id
  sku_name  = "Basic"           # Cost-effective for training
  tags      = var.project_tags
}

# SQL Firewall — allow your training IP
resource "azurerm_mssql_firewall_rule" "allow_my_ip" {
  name             = "AllowTrainingIP"
  server_id        = azurerm_mssql_server.sql.id
  start_ip_address = var.allowed_ip
  end_ip_address   = var.allowed_ip
}

# SQL Firewall — allow Azure services (so VMs can connect)
resource "azurerm_mssql_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.sql.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ══════════════════════════════════════════════
# STEP 6 — Blob Storage & Container
# ══════════════════════════════════════════════
resource "azurerm_storage_account" "storage" {
  name                     = "${var.storage_account_name}${random_string.suffix.result}"
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.project_tags
}

resource "azurerm_storage_container" "reports" {
  name                  = "replenishment-reports"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}
