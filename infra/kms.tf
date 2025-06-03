locals {
  policy_statement_allow_administration = {
    Sid    = "Allow administration of the key",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
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
    Sid    = "KMS KeyUser access",
    Effect = "Allow",
    Principal = {
      AWS = ["arn:aws:iam::${local.immunisation_account_id}:role/auto-ops"]
    },
    Action = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }

  policy_statement_allow_devops = {
    Sid    = "KMS KeyUser access for DevOps",
    Effect = "Allow",
    Principal = {
      AWS = ["arn:aws:iam::${local.immunisation_account_id}:role/DevOps"]
    },
    Action = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    Resource = "*"
  }

  policy_statement_allow_account_a = {
    Sid    = "AllowAccountA",
    Effect = "Allow",
    Principal = {
      AWS = "arn:aws:iam::${local.dspp_core_account_id}:root"
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
