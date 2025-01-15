# First, we create an S3 bucket for compliance reports.
resource "aws_s3_bucket" "backup_reports" {
  bucket = "${var.project_name}-prod-backup-reports"
}

resource "aws_s3_bucket_public_access_block" "backup_reports" {
  bucket = aws_s3_bucket.backup_reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backup_reports" {
  bucket = aws_s3_bucket.backup_reports.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "backup_reports_bucket_policy" {
  bucket = aws_s3_bucket.backup_reports.id

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "backup_reports_bucket_policy"
    Statement = [
      {
        Sid       = "HTTPSOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.backup_reports.arn,
          "${aws_s3_bucket.backup_reports.arn}/*",
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


resource "aws_s3_bucket_ownership_controls" "backup_reports" {
  bucket = aws_s3_bucket.backup_reports.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "backup_reports" {
  depends_on = [aws_s3_bucket_ownership_controls.backup_reports]

  bucket = aws_s3_bucket.backup_reports.id
  acl    = "private"
}

