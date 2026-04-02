resource "aws_s3_bucket" "failed_logs_backup" {
  bucket = "${local.prefix}-failure-logs"
  // To facilitate deletion of non empty busckets
  force_destroy = var.force_destroy
}

data "aws_iam_policy_document" "failed_logs_backup_https_only" {
  statement {
    sid    = "HTTPSOnly"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.failed_logs_backup.arn,
      "${aws_s3_bucket.failed_logs_backup.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "failed_logs_backup_https_only" {
  bucket = aws_s3_bucket.failed_logs_backup.id
  policy = data.aws_iam_policy_document.failed_logs_backup_https_only.json
}
