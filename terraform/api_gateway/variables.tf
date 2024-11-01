variable "prefix" {}
variable "short_prefix" {}
variable "zone_id" {}
variable "api_domain_name" {}
variable "environment" {}
variable "oas" {}

locals {
    environment         = terraform.workspace
    config_env = local.environment == "prod" ? "prod" : "dev"
}
