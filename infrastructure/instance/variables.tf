variable "environment" {
  type        = string
  description = "Environment (AWS Account) name - dev, preprod or prod"
}

variable "sub_environment" {
  type        = string
  description = "Sub-environment name, e.g. internal-dev, internal-qa. The value is set in the Makefile"
}

variable "immunisation_account_id" {
  type        = string
  description = "Immunisation AWS Account ID"
}
variable "dspp_core_account_id" {
  type        = string
  description = "DSPP Core AWS Account ID"
}
variable "csoc_account_id" {
  type        = string
  description = "CSOC AWS Account ID - destination for forwarded logs"
  default     = "693466633220"
}
variable "mns_account_id" {
  type        = string
  description = "MNS AWS account ID - trusted source for MNS notifications"
  default     = "631615744739"
}

variable "dspp_kms_key_alias" {
  description = "Alias name of the DPS KMS key allowed for SSE-KMS encryption"
  type        = string
  default     = "nhsd-dspp-core-ref-extended-attributes-gdp-key"
}

variable "create_mesh_processor" {
  type    = bool
  default = false
}

variable "project_name" {
  type    = string
  default = "immunisation"
}

variable "project_short_name" {
  type    = string
  default = "imms"
}

variable "service" {
  type    = string
  default = "fhir-api"
}

variable "aws_region" {
  default = "eu-west-2"
}

variable "pds_environment" {
  type    = string
  default = "int"
}

# Remember to switch off in PR envs after testing
variable "batch_error_notifications_enabled" {
  default     = true
  description = "Switch to enable batch processing error notifications to Slack"
  type        = bool
}

variable "has_sub_environment_scope" {
  description = "True if the sub-environment is a standalone environment, e.g. internal-dev. False if it is part of a blue-green split, e.g. int-green."
  type        = bool
  default     = false
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
