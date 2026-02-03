terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
  }
  backend "s3" {
    region       = var.aws_region
    key          = "state"
    use_lockfile = true
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "immunisation-fhir-api"
      Environment = var.aws_environment
    }
  }
}


module "mesh" {
  source = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.6"

  name_prefix = "imms-${var.aws_environment}"
  account_id  = var.imms_account_id
  mesh_env    = var.mesh_environment
  subnet_ids  = toset([])
  mailbox_ids = var.mesh_mailbox_ids

  compress_threshold               = 1 * 1024 * 1024
  get_message_max_concurrency      = 10
  handshake_schedule               = "rate(24 hours)"
  fetch_message_lambda_memory_size = var.aws_environment == "prod" ? 512 : 128
}
