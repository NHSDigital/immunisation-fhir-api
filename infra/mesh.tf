# MESH Client Module - conditionally created based on environment configuration
module "mesh" {
  count  = var.mesh_mailbox_id != null ? 1 : 0
  source = "git::https://github.com/nhsdigital/terraform-aws-mesh-client.git//module?ref=v2.1.5"

  name_prefix                    = "imms-${var.environment}"
  account_id                     = var.imms_account_id
  mesh_env                       = var.environment == "prod"? "production" : "integration"
  subnet_ids                     = toset([])
  mailbox_ids                    = [var.mesh_mailbox_id]

  compress_threshold             = 1 * 1024 * 1024
  get_message_max_concurrency    = 10
  handshake_schedule             = "rate(24 hours)"
}
