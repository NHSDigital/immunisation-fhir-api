resource "aws_sqs_queue" "mns_test_notification" {
  count                      = var.mns_environment == "dev" ? 1 : 0
  name                       = "${var.mns_test_notification_name_prefix}-queue"
  fifo_queue                 = false
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 300
}


data "aws_iam_policy_document" "mns_test_notification_sqs_policy" {
  count = var.mns_environment == "dev" ? 1 : 0
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
      aws_sqs_queue.mns_test_notification[0].arn
    ]
  }
}

resource "aws_sqs_queue_policy" "mns_test_notification_sqs" {
  count     = var.mns_environment == "dev" ? 1 : 0
  queue_url = aws_sqs_queue.mns_test_notification[0].id
  policy    = data.aws_iam_policy_document.mns_test_notification_sqs_policy[0].json
}

output "mns_test_queue_url" {
  value       = var.mns_environment == "dev" ? aws_sqs_queue.mns_test_notification[0].url : null
  description = "URL of the MNS test notifications queue"
}

output "mns_test_queue_arn" {
  value       = var.mns_environment == "dev" ? aws_sqs_queue.mns_test_notification[0].arn : 0
  description = "ARN of the MNS test notifications queue"
}

