variable "imms_account_id" {}
variable "aws_environment" {}
variable "mesh_environment" {}
variable "mesh_mailbox_ids" {}
variable "mesh_dlq_mailbox_id" {}
variable "aws_region" {
  type    = string
  default = "eu-west-2"

  validation {
    condition     = var.aws_region == "eu-west-2"
    error_message = "AWS Region must be set to eu-west-2."
  }
}
