variable "prefix" {}
variable "short_prefix" {}
variable "zone_id" {}
variable "api_domain_name" {}
variable "environment" {}
variable "oas" {}
variable "aws_account_name" {}
locals {
  environment = terraform.workspace == "green" ? "prod" : terraform.workspace == "blue" ? "prod" : terraform.workspace
}
