# TODO - move to instance terraform
resource "aws_s3_bucket" "batch_data_source_bucket" {
  bucket        = "immunisation-batch-${local.environment}-data-sources"
  force_destroy = local.is_temp
  tags = {
    "Environment" = local.environment
    "Project"     = "immunisation"
    "Service"     = "fhir-api"
  }
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
  bucket = aws_s3_bucket.batch_data_source_bucket.id
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${local.account_id}:root"
        },
        Action : [
          "s3:PutObject"
        ],
        Resource : [
          "arn:aws:s3:::${aws_s3_bucket.batch_data_source_bucket.bucket}",
          "arn:aws:s3:::${aws_s3_bucket.batch_data_source_bucket.bucket}/*"
        ]
      }
    ]
  })
}

# resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_source_encryption" {
#   bucket = aws_s3_bucket.batch_data_source_bucket.id

#   rule {
#     apply_server_side_encryption_by_default {
#       kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
#       sse_algorithm     = "aws:kms"
#     }
#   }
# }

resource "aws_s3_bucket_lifecycle_configuration" "datasources_lifecycle" {
  bucket = aws_s3_bucket.batch_data_source_bucket.id

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
