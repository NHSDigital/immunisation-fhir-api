data "aws_s3_bucket" "existing_s3_access_log_bucket" {
  count  = var.enable_s3_access_logging ? 1 : 0
  bucket = local.s3_access_log_bucket_name
}

resource "aws_s3_bucket_logging" "batch_data_source_bucket" {
  count         = var.enable_s3_access_logging ? 1 : 0
  bucket        = aws_s3_bucket.batch_data_source_bucket.bucket
  target_bucket = data.aws_s3_bucket.existing_s3_access_log_bucket[0].bucket
  target_prefix = "${aws_s3_bucket.batch_data_source_bucket.bucket}/"
}

resource "aws_s3_bucket_logging" "batch_data_destination_bucket" {
  count         = var.enable_s3_access_logging ? 1 : 0
  bucket        = aws_s3_bucket.batch_data_destination_bucket.bucket
  target_bucket = data.aws_s3_bucket.existing_s3_access_log_bucket[0].bucket
  target_prefix = "${aws_s3_bucket.batch_data_destination_bucket.bucket}/"
}

resource "aws_s3_bucket_logging" "batch_config_bucket" {
  count         = var.enable_s3_access_logging ? 1 : 0
  bucket        = aws_s3_bucket.batch_config_bucket.bucket
  target_bucket = data.aws_s3_bucket.existing_s3_access_log_bucket[0].bucket
  target_prefix = "${aws_s3_bucket.batch_config_bucket.bucket}/"
}

resource "aws_s3_bucket_logging" "account_batch_data_source_bucket" {
  count         = var.enable_s3_access_logging && !var.has_sub_environment_scope ? 1 : 0
  bucket        = "immunisation-batch-${local.resource_scope}-data-sources"
  target_bucket = data.aws_s3_bucket.existing_s3_access_log_bucket[0].bucket
  target_prefix = "immunisation-batch-${local.resource_scope}-data-sources/"
}
