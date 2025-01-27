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
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

variable "region" {
    default = "eu-west-2"
}

data "aws_ssm_parameter" "dest_vault_arn" { 
  name = "/imms/awsbackup/destvaultarn" 
}

data "aws_ssm_parameter" "notified_email" { 
  name = "/imms/awsbackup/email" 
}

data "aws_arn" "destination_vault_arn" {
  arn = data.aws_ssm_parameter.dest_vault_arn.value
}

locals {
  source_account_id = data.aws_caller_identity.current.account_id
  destination_account_id = data.aws_arn.destination_vault_arn.account
  assume_role = "terraform"
}

module "source" {
  source = "./modules/aws_config"

  backup_copy_vault_account_id = local.destination_account_id
  backup_copy_vault_arn        = data.aws_arn.destination_vault_arn.arn
  notifications_target_email_address = data.aws_ssm_parameter.notified_email.value
  environment_name      = "prod"
  project_name          = "imms-fhir-api-"
  terraform_role_arn    = "arn:aws:iam::${local.source_account_id}:role/${local.assume_role}"
  source_account_id     = data.aws_caller_identity.current.account_id
  
  backup_plan_config = {
    "compliance_resource_types" : [
      "S3"
    ],
    "rules" : [
      {
        "copy_action" : {
          "delete_after" : 31
        },
        "lifecycle" : {
          "delete_after" : 4
        },
        "name" : "daily_kept_for_4_days",
        "schedule" : "cron(00 20 * * ? *)"
      }
    ],
    "selection_tag" : "NHSE-Enable-S3-Backup"
  }

  backup_plan_config_dynamodb = {
    "compliance_resource_types" : [
      "DynamoDB"
    ],
    "enable" : true,
    "rules" : [
      {
        "copy_action" : {
          "delete_after" : 31
        },
        "lifecycle" : {
          "delete_after" : 4
        },
        "name" : "daily_kept_for_4_days",
        "schedule" : "cron(00 20 * * ? *)"
      }
    ],
    "selection_tag" : "NHSE-Enable-Dynamo-Backup"
  }
}