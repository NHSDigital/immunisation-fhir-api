resource "aws_sns_topic" "backup" {
  count             = var.notifications_target_email_address != "" ? 1 : 0
  name              = "${local.resource_name_prefix}-notifications"
  kms_master_key_id = aws_kms_key.sns_encrypt_key.arn
  policy            = data.aws_iam_policy_document.allow_backup_to_sns.json
}

data "aws_iam_policy_document" "allow_backup_to_sns" {
  policy_id = "backup"

  statement {
    actions = [
      "SNS:Publish",
    ]

    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }

    resources = ["*"]

    sid = "allow_backup"
  }
}

resource "aws_sns_topic_subscription" "aws_backup_notifications_email_target" {
  count         = var.notifications_target_email_address != "" ? 1 : 0
  topic_arn     = aws_sns_topic.backup[0].arn
  protocol      = "email"
  endpoint      = var.notifications_target_email_address
  filter_policy = jsonencode({ "State" : [{ "anything-but" : "COMPLETED" }] })
}

resource "aws_kms_key" "sns_encrypt_key" {
  description             = "KMS key for AWS Backup notifications"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Sid    = "Enable IAM User Permissions"
        Principal = {
          AWS = "arn:aws:iam::${var.source_account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action   = ["kms:GenerateDataKey*", "kms:Decrypt"]
        Resource = "*"
      },
    ]
  })
}

resource "aws_kms_alias" "sns_encrypt_key" {
  name          = "alias/${var.environment_name}/imms-sns-encryption"
  target_key_id = aws_kms_key.sns_encrypt_key.key_id
}
