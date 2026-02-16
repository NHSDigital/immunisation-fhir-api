module "mns_publisher" {
  source = "./modules/mns_publisher"
  count  = var.mns_publisher_feature_enabled ? 1 : 0

  ddb_delta_stream_arn               = aws_dynamodb_table.delta-dynamodb-table.stream_arn
  dynamo_kms_encryption_key_arn      = data.aws_kms_key.existing_dynamo_encryption_key.arn
  enable_lambda_alarm                = var.error_alarm_notifications_enabled # consider just INT and PROD
  immunisation_account_id            = var.immunisation_account_id
  is_temp                            = local.is_temp
  lambda_kms_encryption_key_arn      = data.aws_kms_key.existing_lambda_encryption_key.arn
  mns_publisher_resource_name_prefix = "${local.resource_scope}-mns-outbound-events"

  private_subnet_ids = local.private_subnet_ids
  security_group_id  = data.aws_security_group.existing_securitygroup.id

  shared_dir_sha              = local.shared_dir_sha
  splunk_firehose_stream_name = module.splunk.firehose_stream_name

  short_prefix = local.short_prefix

  system_alarm_sns_topic_arn = data.aws_sns_topic.imms_system_alert_errors.arn
}
