# main.tf 
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.6.0"
    }
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2.0"
    }
  }
  backend "s3" {
    bucket = "immunisation-grafana-terraform-state"
    region = "eu-west-2"
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
############################################################################################################

resource "null_resource" "vpce_message" {
  count = var.use_natgw ? 0 : 1
  provisioner "local-exec" {
    command = "echo 'Building VPC Endpoint module...'"
  }
}
resource "null_resource" "natgw_message" {
  count = var.use_natgw ? 1 : 0
  provisioner "local-exec" {
    command = "echo 'Building NAT Gateway module...'"
  }
}

# # add vpce module - only if natgw is not used
# module "vpce" {
#   source = "./vpce"
#   count  = var.use_natgw ? 0 : 1
#   aws_region = var.aws_region
#   tags = var.tags
#   prefix = local.prefix
#   private_subnet_ids = aws_subnet.grafana_private[*].id
#   vpc_id = aws_vpc.grafana_main.id
#   ecs_sg_id = aws_security_group.ecs_tasks.id
#   route_table_ids = aws_route_table.private[*].id
# }