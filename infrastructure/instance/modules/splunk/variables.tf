variable "prefix" {}
locals {
  prefix = "${var.prefix}-splunk"
}
variable "splunk_endpoint" {}
variable "hec_token" {}
variable "force_destroy" {}
variable "access_log_target_bucket" {
  type    = string
  default = null
}
