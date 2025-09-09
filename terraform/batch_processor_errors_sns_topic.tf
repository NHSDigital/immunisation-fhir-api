resource "aws_sns_topic" "batch_processor_errors" {
  count = var.batch_error_notifications_enabled ? 1 : 0
  name  = "${local.resource_scope}-batch-processor-errors"
}

resource "aws_sns_topic_policy" "batch_processor_errors_topic_policy" {
  count  = var.batch_error_notifications_enabled ? 1 : 0
  arn    = aws_sns_topic.batch_processor_errors[0].arn
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
        Resource  = aws_sns_topic.batch_processor_errors[0].arn
      }
    ]
  })
}
