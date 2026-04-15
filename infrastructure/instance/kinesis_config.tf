resource "aws_kinesis_stream" "processor_data_streams" {
  name = "${local.short_prefix}-processingdata-stream"
  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  retention_period = var.environment == "prod" ? 24 * 7 : 24
  encryption_type  = "KMS"
  kms_key_id       = data.aws_kms_key.existing_kinesis_encryption_key.arn
}

locals {
  kinesis_arn = aws_kinesis_stream.processor_data_streams.arn
}
