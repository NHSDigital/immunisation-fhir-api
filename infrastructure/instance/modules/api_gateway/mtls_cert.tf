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

resource "aws_s3_bucket_versioning" "truststore_bucket" {
  bucket = aws_s3_bucket.truststore_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_object_copy" "copy_cert_from_storage" {
  bucket = aws_s3_bucket.truststore_bucket.bucket
  key    = local.truststore_file_name
  source = "${data.aws_s3_object.cert.bucket}/${local.truststore_file_name}"
  lifecycle {
    replace_triggered_by = [terraform_data.cert_etag]
  }
}
