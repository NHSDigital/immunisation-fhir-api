resource "aws_kinesis_firehose_delivery_stream" "splunk_firehose_stream" {
    name        = "${local.prefix}-firehose"
    destination = "splunk"

    splunk_configuration {
        hec_endpoint               = var.splunk_endpoint
        hec_token                  = var.hec_token
        hec_acknowledgment_timeout = 180
        retry_duration             = 300
        hec_endpoint_type          = "Event"
        s3_backup_mode             = "FailedEventsOnly"

        s3_configuration {
            role_arn           = aws_iam_role.firehose_role.arn
            bucket_arn         = aws_s3_bucket.failed_logs_backup.arn
            buffering_size     = 10
            buffering_interval = 400
            compression_format = "GZIP"
        }
        cloudwatch_logging_options {
            enabled         = true
            log_group_name   = aws_cloudwatch_log_group.fire_house_logs.name
            log_stream_name = aws_cloudwatch_log_stream.splunk_logs_stream.name
        }
    }
}

resource "aws_cloudwatch_log_group" "fire_house_logs" {
    name = "${local.prefix}-firehose-logs"
}

resource "aws_cloudwatch_log_stream" "splunk_logs_stream" {
    log_group_name = aws_cloudwatch_log_group.fire_house_logs.name
    name           = "splunk"
}