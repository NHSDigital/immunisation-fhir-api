variable "aws_region" {
  default = "eu-west-2"
}

variable "imms_account_id" {
  type = string
}
variable "dspp_account_id" {
  type = string
}
variable "auto_ops_role" {
  type = string
}
variable "admin_role" {
  type = string
}
variable "dev_ops_role" {
  type = string
}

locals {
  account = terraform.workspace # non-prod or prod
  # TODO - add new accounts for CDP migration
}
