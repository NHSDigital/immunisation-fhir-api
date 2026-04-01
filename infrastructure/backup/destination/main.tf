terraform {
  backend "s3" {
    region       = "eu-west-2"
    key          = "state"
    use_lockfile = true
  }
  required_version = ">= 1.5.0"
}

data "aws_caller_identity" "current" {}

module "aws_backup_destination" {
  source = "git::https://github.com/nhsdigital/terraform-aws-backup.git//modules/aws-backup-destination?ref=v1.4.1"

  account_id          = data.aws_caller_identity.current.account_id
  kms_key             = aws_kms_key.destination_backup_key.arn
  source_account_id   = "664418956997" # Immunisation Prod
  source_account_name = "imms-prod"

  # Copied from existing vault - keep or use defaults?
  vault_lock_min_retention_days = 30
  vault_lock_max_retention_days = 60

  # To set once tested
  # enable_vault_protection = true
  # enable_iam_protection = true
  # vault_lock_type = "compliance"
}
