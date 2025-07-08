module "mesh" {
  source                      = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.5"
  name_prefix                 = "local-immunisation"
  mesh_env                    = "integration"
  subnet_ids                  = values(aws_subnet.private)[*].id
  mailbox_ids                 = ["X26OT303"] #TBC
  verify_ssl                  = "true"
  get_message_max_concurrency = 10
  compress_threshold          = 1 * 1024 * 1024
  handshake_schedule          = "rate(24 hours)"
  account_id                  = var.imms_account_id
}
