environment                       = "preprod"
immunisation_account_id           = "084828561157"
dspp_core_account_id              = "603871901111"
pds_environment                   = "int"
mns_environment                   = "int"
error_alarm_notifications_enabled = true

# mesh no invocation period metric set to 3 days (in seconds) for preprod environment i.e 3 * 24 * 60 * 60
mesh_no_invocation_period_seconds       = 259200
create_mesh_processor                   = true
has_sub_environment_scope               = false
dynamodb_point_in_time_recovery_enabled = true
enable_s3_access_logging                = true
s3_access_log_bucket_name               = "immunisation-preprod-s3-access-logs"
