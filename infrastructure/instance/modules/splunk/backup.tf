resource "aws_s3_bucket" "failed_logs_backup" {
  bucket = "${local.prefix}-failure-logs"
  // To facilitate deletion of non empty busckets
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_logging" "failed_logs_backup" {
  count         = var.access_log_target_bucket == null ? 0 : 1
  bucket        = aws_s3_bucket.failed_logs_backup.bucket
  target_bucket = var.access_log_target_bucket
  target_prefix = "${aws_s3_bucket.failed_logs_backup.bucket}/"
}
