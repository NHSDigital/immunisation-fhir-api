variable "environment" {
  type        = string
  description = "Environment (AWS Account) name - dev, preprod or prod"
}

variable "sub_environment" {
  type        = string
  description = "Sub-environment name, e.g. internal-dev, int-blue, blue"
}

variable "has_sub_environment_scope" {
  description = "True if resources are scoped to the sub-environment. False for blue/green shared resources."
  type        = bool
  default     = false
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

variable "immunisation_account_id" {
  type        = string
  description = "Immunisation AWS Account ID"
}

variable "dspp_core_account_id" {
  type        = string
  description = "DSPP Core AWS Account ID"
}

variable "mns_account_id" {
  type        = string
  description = "MNS AWS account ID - trusted source for MNS notifications"
  default     = "631615744739"
}

variable "pds_environment" {
  type    = string
  default = "int"
}

variable "mns_environment" {
  type    = string
  default = "int"
}

variable "error_alarm_notifications_enabled" {
  default     = true
  description = "Switch to enable error alarm notifications to Slack"
  type        = bool
}

variable "create_mesh_processor" {
  type    = bool
  default = false
}

variable "mesh_no_invocation_period_seconds" {
  type    = number
  default = 300
}

variable "dspp_submission_s3_bucket_name" {
  type    = string
  default = "nhsd-dspp-core-ref-s3-submission-upload"
}

variable "dspp_submission_kms_key_alias" {
  type    = string
  default = "nhsd-dspp-core-ref-s3-submission-upload-key"
}

variable "dynamodb_point_in_time_recovery_enabled" {
  type    = bool
  default = false
}
