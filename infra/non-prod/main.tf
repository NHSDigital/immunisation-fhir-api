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

// include the ./grafana/AWS/terraform directory
module "grafana" {
  source = "./grafana/AWS/terraform"
  aws_region = var.aws_region
  cidr_block = data.aws_vpc.default.cidr_block
  vpc_id = data.aws_vpc.default.id
  public_subnet_ids = var.public_subnet_ids
  main_route_table_id = data.aws_route_table.main.id
}