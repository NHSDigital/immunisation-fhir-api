environment                       = "prod"
immunisation_account_id           = "664418956997"
dspp_core_account_id              = "232116723729"
mns_account_id                    = "758334270304"
pds_environment                   = "prod"
error_alarm_notifications_enabled = true

# mesh no invocation period metric set to 1 day (in seconds) for prod environment i.e 1 * 24 * 60 * 60
mesh_no_invocation_period_seconds = 86400
create_mesh_processor             = true
has_sub_environment_scope         = false
dspp_submission_s3_bucket_name    = "nhsd-dspp-core-prod-s3-submission-upload"
dspp_submission_kms_key_alias     = "nhsd-dspp-core-prod-s3-submission-upload-key"
