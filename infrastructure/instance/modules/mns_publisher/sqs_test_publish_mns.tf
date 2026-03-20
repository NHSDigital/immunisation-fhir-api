resource "aws_sqs_queue" "mns_test_notification" {
  count                      = var.enable_mns_test_queue ? 1 : 0
  name                       = "${var.mns_test_notification_name_prefix}-queue"
  fifo_queue                 = false
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 300
}


data "aws_iam_policy_document" "mns_test_notification_sqs_policy" {
  count = var.enable_mns_test_queue ? 1 : 0
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
  count     = var.enable_mns_test_queue ? 1 : 0
  queue_url = aws_sqs_queue.mns_test_notification[0].id
  policy    = data.aws_iam_policy_document.mns_test_notification_sqs_policy[0].json
}
