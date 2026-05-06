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

variable "mns_environment" {
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

variable "has_sub_environment_scope" {
  description = "True if the sub-environment is a standalone environment, e.g. internal-dev. False if it is part of a blue-green split, e.g. int-green."
  type        = bool
  default     = false
}

variable "dynamodb_point_in_time_recovery_enabled" {
  description = "Whether to enable PITR on DynamoDB tables"
  type        = bool
  default     = false
}

variable "recordprocessor_image_uri" {
  description = "Immutable URI of the recordprocessor (batch processor) container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.recordprocessor_image_uri) != ""
    error_message = "recordprocessor_image_uri must be provided."
  }
}

variable "backend_image_uri" {
  description = "Immutable URI of the backend Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.backend_image_uri) != ""
    error_message = "backend_image_uri must be provided."
  }
}

variable "ack_backend_image_uri" {
  description = "Immutable URI of the ack backend Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.ack_backend_image_uri) != ""
    error_message = "ack_backend_image_uri must be provided."
  }
}

variable "batch_processor_filter_image_uri" {
  description = "Immutable URI of the batch processor filter Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.batch_processor_filter_image_uri) != ""
    error_message = "batch_processor_filter_image_uri must be provided."
  }
}

variable "delta_backend_image_uri" {
  description = "Immutable URI of the delta backend Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.delta_backend_image_uri) != ""
    error_message = "delta_backend_image_uri must be provided."
  }
}

variable "filenameprocessor_image_uri" {
  description = "Immutable URI of the filenameprocessor Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.filenameprocessor_image_uri) != ""
    error_message = "filenameprocessor_image_uri must be provided."
  }
}

variable "id_sync_image_uri" {
  description = "Immutable URI of the id sync Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.id_sync_image_uri) != ""
    error_message = "id_sync_image_uri must be provided."
  }
}

variable "mesh_processor_image_uri" {
  description = "Immutable URI of the mesh processor Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.mesh_processor_image_uri) != ""
    error_message = "mesh_processor_image_uri must be provided."
  }
}

variable "mns_publisher_image_uri" {
  description = "Immutable URI of the MNS publisher Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.mns_publisher_image_uri) != ""
    error_message = "mns_publisher_image_uri must be provided."
  }
}

variable "recordforwarder_image_uri" {
  description = "Immutable URI of the recordforwarder Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.recordforwarder_image_uri) != ""
    error_message = "recordforwarder_image_uri must be provided."
  }
}

variable "redis_sync_image_uri" {
  description = "Immutable URI of the redis sync Lambda container image in ECR. Must be supplied by CI/CD."
  type        = string
  default     = ""

  validation {
    condition     = trimspace(var.redis_sync_image_uri) != ""
    error_message = "redis_sync_image_uri must be provided."
  }
}

variable "s3_access_log_bucket_name" {
  description = "Destination bucket used for S3 server access logs"
  type        = string
  default     = ""
}

variable "enable_s3_access_logging" {
  description = "When true, manage S3 server access logging resources in this stack"
  type        = bool
  default     = false
}

locals {
  prefix                    = "${var.project_name}-${var.service}-${var.sub_environment}"
  short_prefix              = "${var.project_short_name}-${var.sub_environment}"
  batch_prefix              = "immunisation-batch-${var.sub_environment}"
  root_domain_name          = "${var.environment}.vds.platform.nhs.uk"
  project_domain_name       = "imms.${local.root_domain_name}"
  service_domain_name       = "${var.sub_environment}.${local.project_domain_name}"
  config_bucket_arn         = aws_s3_bucket.batch_config_bucket.arn
  config_bucket_name        = aws_s3_bucket.batch_config_bucket.bucket
  is_temp                   = length(regexall("[a-z]{2,4}-?[0-9]+", var.sub_environment)) > 0
  resource_scope            = var.has_sub_environment_scope ? var.sub_environment : var.environment
  s3_access_log_bucket_name = var.s3_access_log_bucket_name != "" ? var.s3_access_log_bucket_name : "immunisation-${var.environment}-s3-access-logs"
  # Public subnet - The subnet has a direct route to an internet gateway. Resources in a public subnet can access the public internet.
  # public_subnet_ids = [for k, v in data.aws_route.internet_traffic_route_by_subnet : k if length(v.gateway_id) > 0]
  # Private subnet - The subnet does not have a direct route to an internet gateway. Resources in a private subnet require a NAT device to access the public internet.
  private_subnet_ids = [for k, v in data.aws_route.internet_traffic_route_by_subnet : k if length(v.nat_gateway_id) > 0]
}
