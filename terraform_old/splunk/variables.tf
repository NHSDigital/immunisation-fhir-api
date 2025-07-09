variable "prefix" {}
locals {
    prefix = "${var.prefix}-splunk"
}
variable "splunk_endpoint" {}
variable "hec_token" {}