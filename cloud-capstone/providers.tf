terraform {
  required_version = ">= 1.5.0"

  # ──────────────────────────────────────────────
  # Remote State Backend — Azure Storage
  # Architecture: Remote State → Azure Storage backend
  # Enables team collaboration on shared state
  # ──────────────────────────────────────────────
  backend "azurerm" {
    resource_group_name  = "rg-pharmacy"
    storage_account_name = "ssrstorageaccountk7ozzp"
    container_name       = "tfstate"
    key                  = "pharmacy.terraform.tfstate"
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
}
