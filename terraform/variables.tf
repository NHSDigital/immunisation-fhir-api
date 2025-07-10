variable "environment" {}
variable "sub_environment" {}
variable "aws_account_name" {}
variable "immunisation_account_id" {}
variable "project_name" {
  default = "immunisation"
}

variable "project_short_name" {
  default = "imms"
}

variable "use_new_aws_preprod_account" {
  default = true
}
variable "service" {
  default = "fhir-api"
}

variable "aws_region" {
  default = "eu-west-2"
}

locals {
  prefix       = "${var.project_name}-${var.service}-${var.sub_environment}"
  short_prefix = "${var.project_short_name}-${var.sub_environment}"
  batch_prefix = "immunisation-batch-${var.sub_environment}"

  vpc_name            = "imms-${var.environment}-fhir-api-vpc"
  root_domain         = "${var.sub_environment}.${var.environment}.vds.platform.nhs.uk"
  service_domain_name = "${local.env}.${local.project_domain_name}"
  project_domain_name = data.aws_route53_zone.project_zone.name

  # For now, only create the config bucket in internal-dev and prod as we only have one Redis instance per account.
  create_config_bucket = local.environment == local.config_bucket_env
  config_bucket_arn    = local.create_config_bucket ? aws_s3_bucket.batch_config_bucket[0].arn : data.aws_s3_bucket.existing_config_bucket[0].arn
  config_bucket_name   = local.create_config_bucket ? aws_s3_bucket.batch_config_bucket[0].bucket : data.aws_s3_bucket.existing_config_bucket[0].bucket

  is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.env)) > 0
}
