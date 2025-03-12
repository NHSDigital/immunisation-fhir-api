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
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2.0"
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
  default_tags {
    tags = var.tags
  }
}

provider "aws" {
  alias   = "acm_provider"
  region  = var.aws_region
  profile = "apim-dev"
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
