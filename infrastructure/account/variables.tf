variable "aws_region" {
  type    = string
  default = "eu-west-2"
}
variable "imms_account_id" {
  description = "Immunisation AWS account ID"
  type        = string
}
variable "dspp_account_id" {
  description = "DSPP Core AWS account ID"
  type        = string
}
variable "csoc_account_id" {
  description = "CSOC AWS account ID - destination for log forwarding"
  type        = string
  default     = "693466633220"
}
variable "mns_account_id" {
  type        = string
  description = "MNS AWS account ID - trusted source for MNS notifications"
}

variable "auto_ops_role" {
  default = "role/auto-ops"
  type    = string
}
variable "admin_role" {
  default = "root"
  type    = string
}
variable "dev_ops_role" {
  type = string
}
variable "dspp_admin_role" {
  type = string
}
variable "mns_delivery_role" {
  type    = string
  default = "role/nhs-mns-events-lambda-delivery"
}

variable "build_agent_account_id" {
  type    = string
  default = "958002497996"
}
variable "environment" {
  type        = string
  description = "Immunisation AWS account name (dev / preprod / prod)"
  default     = "dev"
}
variable "blue_green_split" {
  type        = bool
  description = "Whether this account uses blue / green split deployments"
  default     = false
}
