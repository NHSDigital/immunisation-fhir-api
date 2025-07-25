data "aws_secretsmanager_secret" "splunk_token" {
  name = "imms/splunk/${var.aws_account_name}/hec"
}
data "aws_secretsmanager_secret_version" "splunk_token_id" {
  secret_id = data.aws_secretsmanager_secret.splunk_token.id
}

module "splunk" {
  source          = "./splunk"
  prefix          = local.prefix
  splunk_endpoint = "https://firehose.inputs.splunk.aws.digital.nhs.uk/services/collector/event"
  hec_token       = data.aws_secretsmanager_secret_version.splunk_token_id.secret_string
}
