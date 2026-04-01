terraform {
  # backend "s3" {
  #   region       = "eu-west-2"
  #   key          = "state"
  #   use_lockfile = true
  # }
  required_version = ">= 1.5.0"
}

data "aws_caller_identity" "current" {}

data "aws_iam_role" "auto_ops" {
  name = "auto-ops"
}

module "aws_backup_source" {
  source = "git::https://github.com/nhsdigital/terraform-aws-backup.git//modules/aws-backup-source?ref=v1.4.1"

  environment_name             = "prod"
  project_name                 = "ImmsFhirApi"
  backup_copy_vault_account_id = "918296738576"
  backup_copy_vault_arn        = "arn:aws:backup:eu-west-2:918296738576:backup-vault:imms-prod-backup-vault"
  reports_bucket               = "imms-fhir-api-prod-backup-reports"
  bootstrap_kms_key_arn        = aws_kms_key.sns_encrypt_key.arn

  # This is the existing email but not sure if anyone is looking at this mailbox
  notifications_target_email_address = "ImmsFhirAPiBau_VDS@nhs.net"

  # The existing config has this set to a non-existent role called "terraform"
  terraform_role_arns = [data.aws_iam_role.auto_ops.arn]

  # This is the existing backup config. Review retention periods?
  backup_plan_config = {
    "compliance_resource_types" : [
      "S3"
    ],
    "rules" : [
      {
        "copy_action" : {
          "delete_after" : 31
        },
        "lifecycle" : {
          "delete_after" : 4
        },
        "name" : "daily_kept_for_4_days",
        "schedule" : "cron(00 20 * * ? *)"
      }
    ],
    "selection_tag" : "NHSE-Enable-S3-Backup"
  }

  backup_plan_config_dynamodb = {
    "compliance_resource_types" : [
      "DynamoDB"
    ],
    "enable" : true,
    "rules" : [
      {
        "copy_action" : {
          "delete_after" : 31
        },
        "lifecycle" : {
          "delete_after" : 4
        },
        "name" : "daily_kept_for_4_days",
        "schedule" : "cron(00 20 * * ? *)"
      }
    ],
    "selection_tag" : "NHSE-Enable-Dynamo-Backup"
  }
}
