module "mns_publisher" {
  source = "./modules/mns_publisher"

  ddb_delta_stream_arn               = aws_dynamodb_table.delta-dynamodb-table.stream_arn
  dynamo_kms_encryption_key_arn      = data.aws_kms_key.existing_dynamo_encryption_key.arn
  enable_lambda_alarm                = var.error_alarm_notifications_enabled
  immunisation_account_id            = var.immunisation_account_id
  is_temp                            = local.is_temp
  enable_mns_test_queue              = var.mns_environment == "dev"
  resource_scope                     = local.resource_scope
  imms_base_path                     = strcontains(var.sub_environment, "pr-") ? "immunisation-fhir-api/FHIR/R4-${var.sub_environment}" : "immunisation-fhir-api/FHIR/R4"
  lambda_kms_encryption_key_arn      = data.aws_kms_key.existing_lambda_encryption_key.arn
  mns_publisher_resource_name_prefix = "${local.resource_scope}-mns-outbound-events"
  mns_test_notification_name_prefix  = "${local.resource_scope}-mns-test-notification"
  secrets_manager_policy_path        = "${local.policy_path}/secret_manager.json"
  account_id                         = data.aws_caller_identity.current.account_id
  pds_environment                    = var.pds_environment
  mns_environment                    = var.mns_environment

  private_subnet_ids = local.private_subnet_ids
  security_group_id  = data.aws_security_group.existing_securitygroup.id

  image_uri                   = var.mns_publisher_image_uri
  splunk_firehose_stream_name = module.splunk.firehose_stream_name

  short_prefix = local.short_prefix

  system_alarm_sns_topic_arn = data.aws_sns_topic.imms_system_alert_errors.arn
}
