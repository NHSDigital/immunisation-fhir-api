
locals {
  policy_statement_allow_administration = {
    Sid    = "AllowKeyAdministration",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${var.imms_account_id}:role/${var.admin_role}"
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
      AWS = "arn:aws:iam::${var.imms_account_id}:role/${var.auto_ops_role}"
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
      AWS = "arn:aws:iam::${var.imms_account_id}:role/${var.dev_ops_role}"
    },
    Action = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }

  #TODO: This should be renamed (account_a)
  policy_statement_allow_account_a = {
    Sid    = "AllowAccountA",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${var.dspp_account_id}:${var.dspp_admin_role}"
    },
    Action = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }
}


resource "aws_kms_key" "dynamodb_encryption" {
  description         = "KMS key for DynamoDB encryption"
  key_usage           = "ENCRYPT_DECRYPT"
  enable_key_rotation = true
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-default-1",
    Statement = [
      local.policy_statement_allow_administration,
      local.policy_statement_allow_auto_ops,
      local.policy_statement_allow_devops,
      local.policy_statement_allow_account_a
    ]
  })
}

resource "aws_kms_alias" "dynamodb_encryption" {
  name          = "alias/imms-event-dynamodb-encryption"
  target_key_id = aws_kms_key.dynamodb_encryption.key_id
}

resource "aws_kms_key" "kinesis_stream_encryption" {
  description         = "KMS key for kinesis stream encryption"
  key_usage           = "ENCRYPT_DECRYPT"
  enable_key_rotation = true
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-default-1",
    Statement = [
      local.policy_statement_allow_administration,
      local.policy_statement_allow_auto_ops,
      local.policy_statement_allow_devops
    ]
  })
}

resource "aws_kms_alias" "kinesis_stream_encryption" {
  name          = "alias/imms-batch-kinesis-stream-encryption"
  target_key_id = aws_kms_key.kinesis_stream_encryption.key_id
}

resource "aws_kms_key" "lambda_env_encryption" {
  description         = "KMS key for Lambda environment variable encryption"
  key_usage           = "ENCRYPT_DECRYPT"
  enable_key_rotation = true
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-default-1",
    Statement = [
      local.policy_statement_allow_administration,
      local.policy_statement_allow_auto_ops,
      local.policy_statement_allow_devops
    ]
  })
}

resource "aws_kms_alias" "lambda_env_encryption" {
  name          = "alias/imms-batch-lambda-env-encryption"
  target_key_id = aws_kms_key.lambda_env_encryption.key_id
}

resource "aws_kms_key" "s3_shared_key" {
  description         = "KMS key for S3 batch bucket"
  enable_key_rotation = true
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-default-1",
    Statement = [
      local.policy_statement_allow_administration,
      local.policy_statement_allow_account_a
    ]
  })
}

resource "aws_kms_alias" "s3_shared_key" {
  name          = "alias/imms-batch-s3-shared-key"
  target_key_id = aws_kms_key.s3_shared_key.key_id
}
