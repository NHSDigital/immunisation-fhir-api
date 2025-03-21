terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }    
  }
  backend "s3" {
    region = "eu-west-2"
    key    = "state"
  }
    required_version = ">= 1.5.0"
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

module "mesh" {
  source = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.5"

  name_prefix                    = "local-immunisation"
  mesh_env                       = "integration"
  subnet_ids                     = data.aws_subnets.default.ids

  mailbox_ids                    = ["X26OT303"]
  verify_ssl                     = "true"
  get_message_max_concurrency    = 10
  compress_threshold             = 1 * 1024 * 1024
  handshake_schedule             = "rate(24 hours)"

  account_id                     = 345594581768
}