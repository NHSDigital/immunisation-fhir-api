variable "prefix" {}
variable "short_prefix" {}
variable "zone_id" {}
variable "api_domain_name" {}
variable "environment" {}
variable "oas" {}

locals {
  environment = var.environment
  config_env  = var.environment
}
