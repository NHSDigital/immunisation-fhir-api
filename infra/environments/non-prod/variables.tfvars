imms_account_id          = "345594581768"
dspp_account_id          = "603871901111"
mns_account_id           = "631615744739"
admin_role               = "root" # We shouldn't be using the root account. There should be an Admin role
dev_ops_role             = "role/DevOps"
auto_ops_role            = "role/auto-ops"
dspp_admin_role          = "root"
mns_admin_role           = "role/nhs-mns-events-lambda-delivery"
environment              = "dev"
parent_route53_zone_name = "dev.vds.platform.nhs.uk"
child_route53_zone_name  = "imms.dev.vds.platform.nhs.uk"
# TODO - null these out once we're using the int account
# mesh_mailbox_id          = null
# mesh_dlq_mailbox_id      = null
mesh_mailbox_id          = "X26OT303"
mesh_dlq_mailbox_id      = "X26OT304"
