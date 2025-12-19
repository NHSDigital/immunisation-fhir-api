resource "aws_sns_topic" "imms_system_alert_errors" {
  name              = "${var.environment}-imms-system-alert-errors"
  kms_master_key_id = aws_kms_key.error_alerts_sns_encryption_key.arn
}

resource "aws_sns_topic_policy" "imms_system_alert_errors_topic_policy" {
  arn = aws_sns_topic.imms_system_alert_errors.arn
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowCloudWatchToPublish",
        Effect = "Allow",
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        },
        Action   = "SNS:Publish",
        Resource = aws_sns_topic.imms_system_alert_errors.arn
      }
    ]
  })
}
