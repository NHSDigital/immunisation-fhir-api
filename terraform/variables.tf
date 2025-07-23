variable "environment" {}

variable "sub_environment" {
  description = "The value is set in the makefile"
}

variable "immunisation_account_id" {}
variable "dspp_core_account_id" {}

variable "create_mesh_processor" {
  default = false
}

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

variable "pds_environment" {
  default = "int"
}

variable "pds_check_enabled" {
  default = true
}

variable "has_sub_environment_scope" {
  default = false
}

locals {
  prefix              = "${var.project_name}-${var.service}-${var.sub_environment}"
  short_prefix        = "${var.project_short_name}-${var.sub_environment}"
  batch_prefix        = "immunisation-batch-${var.sub_environment}"
  vpc_name            = "imms-${var.environment}-fhir-api-vpc"
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

check "private_subnets" {
  assert {
    condition     = length(local.private_subnet_ids) > 0
    error_message = "No private subnets with internet access found in VPC ${data.aws_vpc.default.id}"
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_route_table" "route_table_by_subnet" {
  for_each = toset(data.aws_subnets.all.ids)

  subnet_id = each.value
}

data "aws_route" "internet_traffic_route_by_subnet" {
  for_each = data.aws_route_table.route_table_by_subnet

  route_table_id         = each.value.id
  destination_cidr_block = "0.0.0.0/0"
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

data "aws_kms_key" "existing_lambda_encryption_key" {
  key_id = "alias/imms-batch-lambda-env-encryption"
}

data "aws_kms_key" "existing_kinesis_encryption_key" {
  key_id = "alias/imms-batch-kinesis-stream-encryption"
}

data "aws_kms_key" "existing_id_sync_sqs_encryption_key" {
  key_id = "alias/imms-event-id-sync-encryption"
}
