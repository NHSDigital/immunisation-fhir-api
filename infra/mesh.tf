module "mesh" {
  source = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.5"

  name_prefix                    = "local-immunisation"
  mesh_env                       = "integration"
  subnet_ids                     = data.aws_subnets.default.ids

  mailbox_ids                    = [local.mesh_mailbox_id]
  verify_ssl                     = "true"
  get_message_max_concurrency    = 10
  compress_threshold             = 1 * 1024 * 1024
  handshake_schedule             = "rate(24 hours)"

  account_id                     = 345594581768
}