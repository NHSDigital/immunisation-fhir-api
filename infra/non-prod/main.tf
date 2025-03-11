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
  region  = var.aws_region
  profile = "apim-dev"
}

provider "aws" {
  alias   = "acm_provider"
  region  = var.aws_region
  profile = "apim-dev"
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

module "grafana" {
  source = "./grafana/terraform"
  aws_region = var.aws_region
  ec2_task_execution_role_name = var.ec2_task_execution_role_name
  ecs_auto_scale_role_name = var.ecs_auto_scale_role_name
  az_count = var.az_count
  app_image = var.app_image
  app_port = var.app_port
  app_count = var.app_count
  health_check_path = var.health_check_path
  fargate_cpu = var.fargate_cpu
  fargate_memory = var.fargate_memory
  cidr_block = var.cidr_block

}