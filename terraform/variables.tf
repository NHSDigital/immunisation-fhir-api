variable "environment" {}

variable "sub_environment" {
  description = "The value is set in the makefile"
}

variable "immunisation_account_id" {}
variable "dspp_core_account_id" {}

# TODO - change this. Get a shared mailbox/switch to Lambda -> Slack integration
# Also should have different config for Prod vs PTL
variable "batch_processor_errors_target_email" {
  default     = "daniel.yip4@nhs.net"
  description = "The target email address for the Batch Processor Errors SNS topic"
  type        = string
}

variable "create_mesh_processor" {
  default = false
}

variable "project_name" {
  default = "immunisation"
}

variable "project_short_name" {
  default = "imms"
}

variable "service" {
  default = "fhir-api"
}

variable "aws_region" {
  default = "eu-west-2"
}

variable "pds_environment" {
  default = "int"
}

variable "pds_check_enabled" {
  default = true
}

variable "has_sub_environment_scope" {
  default = false
}

locals {
  prefix              = "${var.project_name}-${var.service}-${var.sub_environment}"
  short_prefix        = "${var.project_short_name}-${var.sub_environment}"
  batch_prefix        = "immunisation-batch-${var.sub_environment}"
  root_domain_name    = "${var.environment}.vds.platform.nhs.uk"
  project_domain_name = "imms.${local.root_domain_name}"
  service_domain_name = "${var.sub_environment}.${local.project_domain_name}"
  config_bucket_arn   = aws_s3_bucket.batch_config_bucket.arn
  config_bucket_name  = aws_s3_bucket.batch_config_bucket.bucket
  is_temp             = length(regexall("[a-z]{2,4}-?[0-9]+", var.sub_environment)) > 0
  resource_scope      = var.has_sub_environment_scope ? var.sub_environment : var.environment
  # Public subnet - The subnet has a direct route to an internet gateway. Resources in a public subnet can access the public internet.
  # public_subnet_ids = [for k, v in data.aws_route.internet_traffic_route_by_subnet : k if length(v.gateway_id) > 0]
  # Private subnet - The subnet does not have a direct route to an internet gateway. Resources in a private subnet require a NAT device to access the public internet.
  private_subnet_ids = [for k, v in data.aws_route.internet_traffic_route_by_subnet : k if length(v.nat_gateway_id) > 0]
}
