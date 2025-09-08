resource "aws_sns_topic" "batch_processor_errors" {
  name = "${local.short_prefix}-batch-processor-errors"
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

resource "aws_sns_topic_subscription" "batch_processor_errors_email_target" {
  topic_arn     = aws_sns_topic.batch_processor_errors.arn
  protocol      = "email"
  endpoint      = var.batch_processor_errors_target_email
}
