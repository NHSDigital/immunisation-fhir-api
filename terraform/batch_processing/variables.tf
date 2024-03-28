variable "vpc_id" {}
variable "short_prefix" {}
locals {
    prefix = "${var.short_prefix}-batch-processing"
}
variable "task_policy_arn" {}
