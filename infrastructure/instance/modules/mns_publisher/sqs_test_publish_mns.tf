# TODO: Remove when MNS platform authorizes imms-vaccinations-1 event type
# Temporary SQS queue for testing MNS notifications until MNS HTTP endpoint is available

resource "aws_sqs_queue" "mns_test_notification" {
  name                       = "${var.mns_test_notification_name_prefix}-queue"
  fifo_queue                 = false
  message_retention_seconds  = 14400
  visibility_timeout_seconds = 300
}


data "aws_iam_policy_document" "mns_test_notification_sqs_policy" {
  statement {
    sid    = "mns-test-notification-allow-lambda-access"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.mns_publisher_lambda_exec_role.arn]
    }

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.mns_test_notification.arn
    ]
  }
}

resource "aws_sqs_queue_policy" "mns_test_notification_sqs" {
  queue_url = aws_sqs_queue.mns_test_notification.id
  policy    = data.aws_iam_policy_document.mns_test_notification_sqs_policy.json
}

output "mns_test_queue_url" {
  value       = aws_sqs_queue.mns_test_notification.url
  description = "URL of the MNS test notifications queue"
}

output "mns_test_queue_arn" {
  value       = aws_sqs_queue.mns_test_notification.arn
  description = "ARN of the MNS test notifications queue"
}

