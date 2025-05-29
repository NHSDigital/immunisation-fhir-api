terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
  }
}

module "mesh" {
  source = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.5"

  name_prefix                    = "${var.environment}-immunisation"
  mesh_env                       = "local"
  subnet_ids                     = data.aws_subnets.default.ids

  mailbox_ids                    = ["X26OT302", "X26OT303"]
  verify_ssl                     = false

  get_message_max_concurrency    = 10
  compress_threshold             = 1 * 1024 * 1024

  account_id                     = data.aws_caller_identity.current.account_id
}