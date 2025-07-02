variable "aws_region" {
  default = "eu-west-2"
}

variable "imms_account_id" {}
variable "dspp_account_id" {}
variable "auto_ops_role" {}
variable "admin_role" {}
variable "dev_ops_role" {}
variable "dspp_admin_role" {}
variable "parent_route53_zone_name" {}
variable "child_route53_zone_name" {}
variable "build_agent_account_id" {
  default = "958002497996"
}
variable "environment" {
  default = "non-prod"
}
