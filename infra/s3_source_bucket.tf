# Overall entry point into batch in prod. Files are forwarded into the appropriate blue / green bucket.
resource "aws_s3_bucket" "batch_data_source_bucket" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = "immunisation-batch-${var.environment}-data-sources"
}

resource "aws_s3_bucket_public_access_block" "batch_data_source_bucket_public_access_block" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.batch_data_source_bucket[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.batch_data_source_bucket[0].bucket
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${var.dspp_account_id}:root"
        },
        Action : [
          "s3:PutObject"
        ],
        Resource : [
          aws_s3_bucket.batch_data_source_bucket[0].arn,
          "${aws_s3_bucket.batch_data_source_bucket[0].arn}/*"
        ]
      },
      {
        Sid    = "HTTPSOnly"
        Effect = "Deny"
        Principal = {
          "AWS" : "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.batch_data_source_bucket[0].arn,
          "${aws_s3_bucket.batch_data_source_bucket[0].arn}/*",
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

# resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_source_encryption" {
#   count = local.environment == "prod" ? 1 : 0
#   bucket = aws_s3_bucket.batch_data_source_bucket[0].bucket

#   rule {
#     apply_server_side_encryption_by_default {
#       kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
#       sse_algorithm     = "aws:kms"
#     }
#   }
# }

resource "aws_s3_bucket_lifecycle_configuration" "datasources_lifecycle" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.batch_data_source_bucket[0].bucket

  rule {
    id     = "DeleteFilesAfter7Days"
    status = "Enabled"

    filter {
      prefix = "*"
    }

    expiration {
      days = 7
    }
  }
}
