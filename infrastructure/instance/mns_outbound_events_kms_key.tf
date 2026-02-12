resource "aws_kms_key" "mns_outbound_events" {
  description = "KMS key for encrypting MNS outbound immunisation events in SQS"

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
            "kms:EncryptionContext:aws:sqs:arn" = [
              aws_sqs_queue.mns_outbound_events.arn,
              aws_sqs_queue.mns_outbound_events_dlq.arn
            ]
          }
        }
      },
      {
        Sid    = "AllowLambdaToDecrypt"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.mns_publisher_lambda_exec_role.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "mns_outbound_events_key" {
  name          = "alias/mns-outbound-events-key"
  target_key_id = aws_kms_key.mns_outbound_events.id
}
