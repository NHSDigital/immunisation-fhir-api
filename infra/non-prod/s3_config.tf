resource "aws_s3_bucket" "batch_config_bucket" {
    bucket        = "imms-internal-dev-supplier-config"

    tags                        = {
      "NHSE-Enable-S3-Backup" = "True"
    }
}

resource "aws_s3_bucket_public_access_block" "batch_config_bucket_public_access_block" {
  bucket = aws_s3_bucket.batch_config_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "batch_config_bucket_policy" {
  bucket = aws_s3_bucket.batch_config_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "batch_config_bucket_policy"
    Statement = [
      {
        Sid       = "HTTPSOnly"
        Effect    = "Deny"
        Principal = {
          AWS = "arn:aws:iam::${local.local_account_id}:root"
        }
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.batch_config_bucket.arn,
          "${aws_s3_bucket.batch_config_bucket.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
}
