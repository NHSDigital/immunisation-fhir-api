# NOTE. This is a temporary file.
# Eventually the aws_kms_key "id_sync_sqs_key" will go into infra/kms.tf

locals {

  # from infra/environments/non-prod/variables.tfvars
  # NOTE: this is only going to work in non-prod for now.

  imms_account_id          = "345594581768"
  admin_role               = "root"
  dev_ops_role             = "role/DevOps"
  auto_ops_role            = "role/auto-ops"

  # from infra/kms.tf

  policy_statement_allow_administration = {
    Sid    = "AllowKeyAdministration",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${local.imms_account_id}:${local.admin_role}"
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
      AWS = "arn:aws:iam::${local.imms_account_id}:${local.auto_ops_role}"
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
      AWS = "arn:aws:iam::${local.imms_account_id}:${local.dev_ops_role}"
    },
    Action = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }

  # -- New elements relating to id_sync are below here

  # MNS id/role: ultimately these should go in infra/environments/<env>/variables.tfvars

  mns_account_id    = "631615744739"
  mns_admin_role    = "role/nhs-mns-events-lambda-delivery"

  policy_statement_allow_mns = {
    Sid    = "AllowMNSLambdaDelivery",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${local.mns_account_id}:${local.mns_admin_role}"
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
