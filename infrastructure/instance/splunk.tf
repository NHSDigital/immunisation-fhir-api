data "aws_secretsmanager_secret" "splunk_token" {
  name = "imms/splunk/${var.environment}/hec"
}
data "aws_secretsmanager_secret_version" "splunk_token_id" {
  secret_id = data.aws_secretsmanager_secret.splunk_token.id
}

module "splunk" {
  source                   = "./modules/splunk"
  prefix                   = local.prefix
  splunk_endpoint          = "https://firehose.inputs.splunk.aws.digital.nhs.uk/services/collector/event"
  hec_token                = data.aws_secretsmanager_secret_version.splunk_token_id.secret_string
  force_destroy            = local.is_temp
  access_log_target_bucket = var.enable_s3_access_logging ? local.s3_access_log_bucket_name : null
}
