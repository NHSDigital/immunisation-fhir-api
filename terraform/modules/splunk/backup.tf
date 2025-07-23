resource "aws_s3_bucket" "failed_logs_backup" {
  bucket = "${local.prefix}-failure-logs"
  // To facilitate deletion of non empty busckets
  force_destroy = var.force_destroy
}
