# Create s3 Bucket with conditional destroy for pr environments
resource "aws_s3_bucket" "data_quality_reports_bucket" {
    bucket      = "imms-${local.short_prefix}-data_quality_reports"
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


resource "aws_s3_bucket_versioning" "dq_source_versioning" {
  bucket = aws_s3_bucket.data_quality_reports_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}