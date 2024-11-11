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
    environment         = terraform.workspace
    prefix              = "${var.project_name}-${var.service}-${local.environment}"
    short_prefix        = "${var.project_short_name}-${local.environment}"
    service_domain_name = "${local.environment}.${local.project_domain_name}"
    config_env = local.environment == "prod" ? "prod" : "dev"

    tags = {
        Project     = var.project_name
        Environment = local.environment
        Service     = var.service
    }
}

variable "region" {
    default = "eu-west-2"
}

data "aws_kinesis_stream" "existing_kinesis_stream" {
     name = "imms-batch-${local.environment}-processingdata-stream" 
}

data "aws_kms_key" "existing_kinesis_encryption_key" {
  key_id = "alias/imms-batch-kinesis-stream-encryption"
}