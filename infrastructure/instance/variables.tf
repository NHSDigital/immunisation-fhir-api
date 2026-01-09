variable "environment" {}

variable "sub_environment" {
  description = "The value is set in the makefile"
}

variable "immunisation_account_id" {}
variable "dspp_core_account_id" {}
variable "csoc_account_id" {
  default = "693466633220"
}

variable "dspp_kms_key_alias" {
  description = "Alias name of the DPS KMS key allowed for SSE-KMS encryption"
  type        = string
  default     = "nhsd-dspp-core-ref-extended-attributes-gdp-key"
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

variable "mesh_no_invocation_period_seconds" {
  description = "The maximum duration the MESH Processor Lambda can go without being invoked before the no-invocation alarm is triggered."
  type        = number
  default     = 300
}

# Remember to switch off in PR envs after testing
variable "error_alarm_notifications_enabled" {
  default     = true
  description = "Switch to enable error alarm notifications to Slack"
  type        = bool
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
