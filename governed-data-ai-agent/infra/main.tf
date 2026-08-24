terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" { features {} }

variable "environment" { type = string }
variable "location" { type = string default = "eastus" }
variable "resource_group_name" { type = string default = "rg-governed-ai" }

resource "azurerm_resource_group" "this" {
  name     = "${var.resource_group_name}-${var.environment}"
  location = var.location
  tags = {
    environment = var.environment
    governance  = "required"
    owner       = "data-platform"
  }
}

# Extend this module with Databricks, ADLS Gen2, Key Vault, Purview-linked resources,
# private networking, and managed identities in the target Azure subscription.
