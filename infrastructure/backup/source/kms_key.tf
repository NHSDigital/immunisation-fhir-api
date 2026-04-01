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
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
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
      {
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
        Action   = ["kms:GenerateDataKey*", "kms:Decrypt"]
        Resource = "*"
      },
    ]
  })
}

resource "aws_kms_alias" "sns_encrypt_key" {
  name          = "alias/prod/imms-sns-encryption"
  target_key_id = aws_kms_key.sns_encrypt_key.key_id
}
