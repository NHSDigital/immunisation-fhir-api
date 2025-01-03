terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.0.2"
    }
  }
  backend "s3" {
    region = "eu-west-2"
    key    = "state"
  }
    required_version = ">= 1.5.0"
}

provider "aws" {
  region  = var.region
  profile = "apim-dev"
  default_tags {
    tags = {
         Environment = local.environment
      }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_ssm_parameter" "src_acct_id" { 
  name = "/imms/awsbackup/dev/sourceacctid" 
}

data "aws_ssm_parameter" "src_acct_name" { 
  name = "/imms/awsbackup/dev/sourceacctname" 
}

module "destination" {
  source = "./modules/aws_config"
  source_account_id       = data.aws_ssm_parameter.src_acct_id.value
  source_account_name     = data.aws_ssm_parameter.src_acct_name.value
  account_id              = local.destination_account_id
  enable_vault_protection = true
}

locals {
  environment         = terraform.workspace
  destination_account_id = data.aws_caller_identity.current.account_id
}

variable "region" {
    default = "eu-west-2"
}