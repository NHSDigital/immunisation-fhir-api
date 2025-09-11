resource "aws_sns_topic" "batch_processor_errors" {
  name              = "${var.environment}-batch-processor-errors"
  kms_master_key_id = aws_kms_key.batch_processor_errors_sns_encryption_key.arn
}

resource "aws_sns_topic_policy" "batch_processor_errors_topic_policy" {
  arn    = aws_sns_topic.batch_processor_errors.arn
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowCloudWatchToPublish",
        Effect    = "Allow",
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        },
        Action    = "SNS:Publish",
        Resource  = aws_sns_topic.batch_processor_errors.arn
      }
    ]
  })
}
