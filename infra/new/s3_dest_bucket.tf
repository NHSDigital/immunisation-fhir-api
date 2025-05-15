# TODO - move to instance terraform
resource "aws_s3_bucket" "batch_data_destination_bucket" {
  bucket        = "immunisation-batch-${local.environment}-data-destinations"
  force_destroy = local.is_temp
  tags = {
    "Environment" = local.environment
    "Project"     = "immunisation"
    "Service"     = "fhir-api"
  }
}

resource "aws_s3_bucket_policy" "batch_data_destination_bucket_policy" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${local.account_id}:root"
        },
        Action : [
          "s3:ListBucket",
          "s3:GetObject"
        ],
        Resource : [
          "arn:aws:s3:::${aws_s3_bucket.batch_data_destination_bucket.bucket}",
          "arn:aws:s3:::${aws_s3_bucket.batch_data_destination_bucket.bucket}/*"
        ]
      }
    ]
  })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_destination_encryption" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_destinations" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id

  rule {
    id     = "DeleteFilesFromForwardedFile"
    status = "Enabled"

    filter {
      prefix = "forwardedFile/"
    }

    expiration {
      days = 14
    }
  }

  rule {
    id     = "DeleteFilesFromAckFolder"
    status = "Enabled"

    filter {
      prefix = "ack/"
    }

    expiration {
      days = 14
    }
  }
}
