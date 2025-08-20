variable "aws_region" {
    type = string
  default = "eu-west-2"
}
variable "imms_account_id" {
    description = "Immunisation AWS account ID"
    type = string
}
variable "dspp_account_id" {
    description = "DSPP Core AWS account ID"
    type = string
}
variable "auto_ops_role" {
    default = "role/auto-ops"
    type = string
}
variable "admin_role" {
    type = string
}
variable "dev_ops_role" {
    type = string
}
variable "dspp_admin_role" {
    type = string
}
variable "build_agent_account_id" {
    type = string
  default = "958002497996"
}
variable "environment" {
    type = string
    description = "Immunisation AWS account name (dev / preprod / prod)"
  default = "dev"
}
variable "blue_green_split" {
    type = bool
    description = "Whether this account uses blue / green split deployments"
    default = false
}

variable "mns_account_id" {}
variable "mns_admin_role" {}
