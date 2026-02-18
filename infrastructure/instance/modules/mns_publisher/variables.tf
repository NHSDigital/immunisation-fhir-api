variable "aws_region" {
  type        = string
  default     = "eu-west-2"
  description = "The AWS region to deploy the module into. Only accept eu-west-2."

  validation {
    condition     = var.aws_region == "eu-west-2"
    error_message = "AWS Region must be set to eu-west-2."
  }
}

variable "ddb_delta_stream_arn" {
  type        = string
  description = "The ARN of the Delta Dynamo DB Stream which the feature consumes from."
}

variable "dynamo_kms_encryption_key_arn" {
  type        = string
  description = "The ARN of the KMS encryption key used on data in Dynamo DB."
}

variable "enable_lambda_alarm" {
  type        = bool
  description = "Switch to enable an error alarm for the MNS Publisher Lambda function."
}

variable "immunisation_account_id" {
  type        = string
  description = "Immunisation AWS Account ID."
}

variable "is_temp" {
  type        = bool
  description = "Flag to state if this is a temporary environment. E.g. PR environment. Used for deletion logic."
}

variable "lambda_kms_encryption_key_arn" {
  type        = string
  description = "The ARN of the KMS encryption key used to encrypt Lambda function environment variables."
}

variable "mns_publisher_resource_name_prefix" {
  type        = string
  description = "The prefix for the name of resources within the mns_publisher feature."
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "shared_dir_sha" {
  type        = string
  description = "The SHA of the shared Lambda code directory. Used for determining if a change occurred there so the Lambda function needs rebuilding."
}

variable "splunk_firehose_stream_name" {
  type        = string
  description = "The name of the Splunk delivery stream."
}

variable "short_prefix" {
  type        = string
  description = "The short prefix used for the Lambda function. Constructed and defined by the calling module, but is typically imms-internal-qa, imms-int-green etc."
}

variable "system_alarm_sns_topic_arn" {
  type        = string
  description = "The ARN of the SNS Topic used for raising alerts to Slack for CW alarms."
}

variable "resource_scope" {
  type        = string
  description = "The effective deployment scope used for resource naming and isolation."
}


variable "sub_environment" {
  type        = string
  description = "Sub-environment name, e.g. internal-dev, internal-qa. The value is set in the Makefile"
}
