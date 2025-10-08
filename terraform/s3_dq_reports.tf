# Create s3 Bucket with conditional destroy for pr environments
resource "aws_s3_bucket" "data_quality_reports_bucket" {
    bucket      = "${local.short_prefix}-data-quality-reports"
    force_destroy = local.is_temp

}

# Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "data_quality_reports_bucket_public_access_block" {
  bucket = aws_s3_bucket.data_quality_reports_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "data_quality_reports" {
  bucket = aws_s3_bucket.data_quality_reports_bucket.id

  rule {
    id     = "GenericValidationReports"
    status = "Enabled"

    filter {
    }

    expiration {
      days = 14
    }
  }
}


# Add versioning to prevent against accidental deletes
resource "aws_s3_bucket_versioning" "dq_source_versioning" {
  bucket = aws_s3_bucket.data_quality_reports_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}


# If used should attached to lambda or any aws service that needs to perform any operation
resource "aws_iam_policy" "s3_dq_access" {
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data_quality_reports_bucket.arn,
          "${aws_s3_bucket.data_quality_reports_bucket.arn}/*"
        ]
      }
    ]
  })
}