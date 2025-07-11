module "mesh" {
  source = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.5"

  name_prefix                    = "local-immunisation"
  mesh_env                       = "integration"
  subnet_ids                     = data.aws_subnets.default.ids

  # TODO single or many mailbox ids
  mailbox_ids                    = [var.mesh_mailbox_id]
  dlq_mailbox_id                 = var.mesh_dlq_mailbox_id
  verify_ssl                     = "true"
  get_message_max_concurrency    = 10
  compress_threshold             = 1 * 1024 * 1024
  handshake_schedule             = "rate(24 hours)"

  account_id                     = local.immunisation_account_id
  # TODO these bucket names need attention - enviroment specific names to avoid conflicts
  mesh_bucket_name              = "imms-${var.environment}-mesh-data-sources"
  mesh_logs_bucket_name         = "imms-${var.environment}-mesh-s3logs"
}