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
  default = true
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
  environment         = terraform.workspace == "green" ? "prod" : terraform.workspace == "blue" ? "prod" : terraform.workspace
  env                 = terraform.workspace
  prefix              = "${var.project_name}-${var.service}-${local.env}"
  short_prefix        = "${var.project_short_name}-${local.env}"
  batch_prefix        = "immunisation-batch-${local.env}"
  service_domain_name = "${local.env}.${local.project_domain_name}"
  config_env          = local.environment == "prod" ? "prod" : "dev"
  config_bucket_env   = local.environment == "prod" ? "prod" : "internal-dev"

  tags = {
    Project     = var.project_name
    Environment = local.environment
    Service     = var.service
  }
}

variable "aws_region" {
  default = "eu-west-2"
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
  bucket = "imms-${local.config_bucket_env}-supplier-config"
}

data "aws_s3_bucket" "existing_destination_bucket" {
  bucket = "immunisation-batch-${local.local_config}-data-destinations"
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
