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

variable "dspp_submission_s3_bucket_name" {
  description = "Name of the DSPP (DPS) S3 bucket where extended attributes files should be submitted"
  type        = string
  default     = "nhsd-dspp-core-ref-s3-submission-upload"
}

variable "dspp_submission_kms_key_alias" {
  description = "Alias of the DSPP (DPS) KMS key required to encrypt extended attributes files"
  type        = string
  default     = "nhsd-dspp-core-ref-s3-submission-upload-key"
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
  type    = string
  default = "eu-west-2"

  validation {
    condition     = var.aws_region == "eu-west-2"
    error_message = "AWS Region must be set to eu-west-2."
  }
}

variable "pds_environment" {
  type    = string
  default = "int"
}

variable "mesh_no_invocation_period_seconds" {
  description = "The maximum duration the MESH Processor Lambda can go without being invoked before the no-invocation alarm is triggered."
  type        = number
  default     = 300
}

variable "error_alarm_notifications_enabled" {
  default     = true
  description = "Switch to enable error alarm notifications to Slack"
  type        = bool
}

variable "mns_publisher_feature_enabled" {
  default     = false
  description = "Switch to the MNS Publisher feature which allows us to publish Immunisation events."
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
