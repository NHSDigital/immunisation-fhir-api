terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
    # TODO - do we need docker?
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
  default_tags {
    tags = {
      Project     = "immunisation-fhir-api"
      Environment = local.environment
    }
  }
}

# TODO - use these instead of some of the hard coded values?
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
