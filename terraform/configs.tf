locals {
  // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
  is_temp                 = length(regexall("[a-z]{2,4}-?[0-9]+", local.env)) > 0
  dspp_core_account_id    = local.environment == "prod" ? 232116723729 : 603871901111
  immunisation_account_id = local.environment == "prod" ? 664418956997 : 345594581768
  
  // MESH Mailbox IDs by environment
  prod_mesh_mailbox_id = "X26HC138"
  prod_mesh_dlq_mailbox_id = null
  int_mesh_mailbox_id  = "X26OT303"
  int_mesh_dlq_mailbox_id = "X26OT304"
  
  // Environment-specific MESH configuration
  // Note: Prod and int names are hardcoded, dev is variable
  mesh_mailbox_id = local.environment == "prod" ? local.prod_mesh_mailbox_id : (
    local.environment == "int" ? local.int_mesh_mailbox_id : var.dev_mesh_mailbox_id
  )
  
  // DLQ Mailbox for int only - Not currently implemented TODO
  mesh_dlq_mailbox_id = local.environment == "prod" ? local.prod_mesh_dlq_mailbox_id : (
    local.environment == "int" ? local.int_mesh_dlq_mailbox_id :
    var.dev_mesh_dlq_mailbox_id
  )

  // MESH enabled if mailbox ID not null
  is_mesh_enabled = local.mesh_mailbox_id != null
}