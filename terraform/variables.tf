variable "project_name" {
  default = "immunisations"
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

locals {
  environment       = terraform.workspace == "green" ? "prod" : terraform.workspace == "blue" ? "prod" : terraform.workspace
  env               = terraform.workspace
  prefix            = "${var.project_name}-${var.service}-${local.env}"
  short_prefix      = "${var.project_short_name}-${local.env}"
  batch_prefix      = "immunisation-batch-${local.env}"
  config_env        = local.environment == "prod" ? "prod" : "dev"
  config_bucket_env = local.environment == "prod" ? "prod" : "internal-dev"

  root_domain         = "${local.config_env}.vds.platform.nhs.uk"
  project_domain_name = data.aws_route53_zone.project_zone.name
  service_domain_name = "${local.env}.${local.project_domain_name}"

  # For now, only create the config bucket in internal-dev and prod as we only have one Redis instance per account.
  create_config_bucket = local.environment == local.config_bucket_env
  config_bucket_arn    = local.create_config_bucket ? aws_s3_bucket.batch_config_bucket[0].arn : data.aws_s3_bucket.existing_config_bucket[0].arn
  config_bucket_name   = local.create_config_bucket ? aws_s3_bucket.batch_config_bucket[0].bucket : data.aws_s3_bucket.existing_config_bucket[0].bucket
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_kms_key" "existing_s3_encryption_key" {
  key_id = "alias/imms-batch-s3-shared-key"
}

data "aws_kms_key" "existing_dynamo_encryption_key" {
  key_id = "alias/imms-event-dynamodb-encryption"
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
  # For now, look up the internal-dev bucket during int, ref and PR branch deploys.
  count = local.create_config_bucket ? 0 : 1

  bucket = "imms-${local.config_bucket_env}-supplier-config"
}

data "aws_kms_key" "existing_lambda_encryption_key" {
  key_id = "alias/imms-batch-lambda-env-encryption"
}

data "aws_kms_key" "existing_kinesis_encryption_key" {
  key_id = "alias/imms-batch-kinesis-stream-encryption"
}

data "aws_kms_key" "mesh_s3_encryption_key" {
  key_id = "alias/local-immunisation-mesh"
}
