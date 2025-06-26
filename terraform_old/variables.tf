variable "profile" {
  default = "apim-dev"
}
variable "aws_account_name" {
  default = "non-prod"
}
variable "project_name" {
  default = "immunisations"
}

variable "project_short_name" {
  default = "imms"
}

variable "service" {
  default = "fhir-api"
}

data "aws_vpc" "default" {
  filter {
    name   = "tag:Name"
    values = [local.vpc_name]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  root_domain = "${local.config_env}.vds.platform.nhs.uk"
}

locals {
  project_domain_name = data.aws_route53_zone.project_zone.name
}

locals {
  environment             = var.aws_account_name
  env                     = terraform.workspace
  prefix                  = "${var.project_name}-${var.service}-${local.env}"
  short_prefix            = "${var.project_short_name}-${local.env}"
  batch_prefix            = "immunisation-batch-${local.env}"
  service_domain_name     = "${local.env}.${local.project_domain_name}"
  config_env              = local.environment
  vpc_name                = "imms-${local.config_env}-fhir-api-vpc"
  immunisation_account_id = "084828561157"
  dspp_core_account_id    = "603871901111"
  local_config            = "int"
  tags = {
    Project     = var.project_name
    Environment = local.environment
    Service     = var.service
  }
}

variable "region" {
  default = "eu-west-2"
}

data "aws_kms_key" "existing_s3_encryption_key" {
  key_id = "alias/imms-batch-s3-shared-key"
}

data "aws_kms_key" "existing_dynamo_encryption_key" {
  key_id = "alias/imms-event-dynamodb-encryption"
}

variable "aws_region" {
  default = "eu-west-2"
}

data "aws_elasticache_cluster" "existing_redis" {
  cluster_id = "immunisation-redis-cluster"
}

data "aws_security_group" "existing_securitygroup" {
  filter {
    name   = "group-name"
    values = ["immunisation-security-group"]
  }
}

data "aws_s3_bucket" "existing_config_bucket" {
  bucket = "imms-int-supplier-config"
}

data "aws_s3_bucket" "existing_destination_bucket" {
  bucket = "immunisation-batch-${var.aws_account_name}-preprod-data-destinations"
}

data "aws_s3_bucket" "existing_source_bucket" {
  bucket = "immunisation-batch-${var.aws_account_name}-preprod-data-sources"
}

data "aws_kms_key" "existing_lambda_encryption_key" {
  key_id = "alias/imms-batch-lambda-env-encryption"
}

data "aws_kms_key" "existing_kinesis_encryption_key" {
  key_id = "alias/imms-batch-kinesis-stream-encryption"
}

data "aws_dynamodb_table" "events-dynamodb-table" {
  name = "imms-${var.aws_account_name}-imms-events"
}

data "aws_dynamodb_table" "audit-table" {
  name = "immunisation-batch-${var.aws_account_name}-audit-table"
}

data "aws_dynamodb_table" "delta-dynamodb-table" {
  name = "imms-${var.aws_account_name}-delta"
}

data "aws_lambda_function" "existing_file_name_proc_lambda" {
  function_name = aws_lambda_function.file_processor_lambda.function_name
}

