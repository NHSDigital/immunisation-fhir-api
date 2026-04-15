resource "aws_kms_key" "mns_outbound_events" {
  description         = "KMS key for encrypting MNS outbound immunisation events in SQS"
  key_usage           = "ENCRYPT_DECRYPT"
  enable_key_rotation = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.immunisation_account_id}:root"
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
      },
      {
        Sid    = "AllowSQSUseOfKey"
        Effect = "Allow"
        Principal = {
          Service = "sqs.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey",
          "kms:Decrypt"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:EncryptionContext:aws:sqs:queue_arn" = [
              "arn:aws:sqs:${var.aws_region}:${var.immunisation_account_id}:${var.mns_publisher_resource_name_prefix}-queue",
              "arn:aws:sqs:${var.aws_region}:${var.immunisation_account_id}:${var.mns_publisher_resource_name_prefix}-dead-letter-queue"
            ]
          }
        }
      },
      {
        Sid    = "AllowLambdaToDecrypt"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.immunisation_account_id}:role/${var.short_prefix}-mns-publisher-lambda-exec-role"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowEventBridgePipesUseOfKey"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.immunisation_account_id}:role/${var.mns_publisher_resource_name_prefix}-eventbridge-pipe-role"
        }
        Action = [
          "kms:GenerateDataKey",
          "kms:Encrypt",
          "kms:DescribeKey"

        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "mns_outbound_events_key" {
  name          = "alias/${var.mns_publisher_resource_name_prefix}-key"
  target_key_id = aws_kms_key.mns_outbound_events.id
}
