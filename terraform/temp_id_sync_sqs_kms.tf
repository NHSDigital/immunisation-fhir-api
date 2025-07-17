# NOTE. This is a temporary file.
# Eventually the aws_kms_key "id_sync_sqs_key" will go into infra/kms.tf

locals {
  policy_statement_allow_administration = {
    Sid    = "AllowKeyAdministration",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${var.imms_account_id}:${var.admin_role}"
    },
    Action = [
      "kms:Create*",
      "kms:Describe*",
      "kms:Enable*",
      "kms:List*",
      "kms:Put*",
      "kms:Update*",
      "kms:Revoke*",
      "kms:Disable*",
      "kms:Get*",
      "kms:Delete*",
      "kms:ScheduleKeyDeletion",
      "kms:CancelKeyDeletion",
      "kms:GenerateDataKey*",
      "kms:Decrypt",
      "kms:Tag*"
    ],
    Resource = "*"
  }

  policy_statement_allow_auto_ops = {
    Sid    = "KMSKeyUserAccess",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${var.imms_account_id}:${var.auto_ops_role}"
    },
    Action = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }

  policy_statement_allow_devops = {
    Sid    = "KMSKeyUserAccessForDevOps",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${var.imms_account_id}:${var.dev_ops_role}"
    },
    Action = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }

  # New elements relating to id_sync are below here

  # mns_account_id: ultimately these should go in infra/environments/<env>/variables.tfvars
  mns_account_id    = local.environment == "prod" ? 758334270304 : 631615744739
  mns_admin_role    = "role"

  policy_statement_allow_mns = {
    Sid    = "AllowMNSLambdaDelivery",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${local.mns_account_id}:${local.mns_admin_role}/nhs-mns-events-lambda-delivery"
    },
    Action = "kms:GenerateDataKey",
    Resource = "*"
  }
}

resource "aws_kms_key" "id_sync_sqs_encryption" {
  description         = "KMS key for MNS service access"
  key_usage           = "ENCRYPT_DECRYPT"
  enable_key_rotation = true
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-consolepolicy-3",
    Statement = [
      local.policy_statement_allow_administration,
      local.policy_statement_allow_auto_ops,
      local.policy_statement_allow_devops,
      local.policy_statement_allow_mns
    ]
  })
}

resource "aws_kms_alias" "id_sync_sqs_encryption" {
  name          = "alias/imms-event-id-sync-sqs-encryption"
  target_key_id = aws_kms_key.id_sync_sqs_encryption.key_id
}
