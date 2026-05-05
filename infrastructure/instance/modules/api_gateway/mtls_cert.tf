locals {
  # NHSD cert file
  truststore_file_name = var.environment == "preprod" ? "imms-int-cert.pem" : "server-renewed-cert.pem"
}

data "aws_s3_bucket" "cert_storage" {
  bucket = "imms-fhir-${var.environment}-cert-storage"
}

data "aws_s3_object" "cert" {
  bucket = data.aws_s3_bucket.cert_storage.bucket
  key    = local.truststore_file_name
}

resource "terraform_data" "cert_etag" {
  input = data.aws_s3_object.cert.etag
}

resource "aws_s3_bucket" "truststore_bucket" {
  bucket        = "${var.prefix}-truststores"
  force_destroy = true
}

resource "aws_s3_bucket_logging" "truststore_bucket" {
  count         = var.access_log_target_bucket == null ? 0 : 1
  bucket        = aws_s3_bucket.truststore_bucket.bucket
  target_bucket = var.access_log_target_bucket
  target_prefix = "${aws_s3_bucket.truststore_bucket.bucket}/"
}

resource "aws_s3_bucket_versioning" "truststore_bucket" {
  bucket = aws_s3_bucket.truststore_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}

data "aws_iam_policy_document" "cert_storage_https_only_s3_policy" {
  statement {
    sid    = "HTTPSOnly"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      data.aws_s3_bucket.cert_storage.arn,
      "${data.aws_s3_bucket.cert_storage.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

data "aws_iam_policy_document" "truststore_https_only_s3_policy" {
  statement {
    sid    = "HTTPSOnly"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.truststore_bucket.arn,
      "${aws_s3_bucket.truststore_bucket.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "cert_storage_https_only" {
  bucket = data.aws_s3_bucket.cert_storage.id
  policy = data.aws_iam_policy_document.cert_storage_https_only_s3_policy.json
}

resource "aws_s3_bucket_policy" "truststore_https_only" {
  bucket = aws_s3_bucket.truststore_bucket.id
  policy = data.aws_iam_policy_document.truststore_https_only_s3_policy.json
}

resource "aws_s3_object_copy" "copy_cert_from_storage" {
  bucket = aws_s3_bucket.truststore_bucket.bucket
  key    = local.truststore_file_name
  source = "${data.aws_s3_object.cert.bucket}/${local.truststore_file_name}"
  lifecycle {
    replace_triggered_by = [terraform_data.cert_etag]
  }
}
