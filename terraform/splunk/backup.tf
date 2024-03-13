resource "aws_s3_bucket" "failed_logs_backup" {
    bucket = "${local.prefix}-failed-logs"
}
