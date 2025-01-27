resource "aws_kms_key" "destination_backup_key" {
  description             = "KMS key for AWS Backup vaults"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Sid    = "Enable IAM User Permissions"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "destination_backup_key" {
  name          = "alias/${local.environment}/imms-bkp-encryption"
  target_key_id = aws_kms_key.destination_backup_key.key_id
}