variable "vpc_id" {}
variable "prefix" {}
locals {
    prefix = "${var.prefix}-batch-processing"
}
