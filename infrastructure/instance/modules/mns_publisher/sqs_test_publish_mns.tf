# Main queue for MNS notification testing
resource "aws_sqs_queue" "mns_test_notification" {
  name                       = "${var.mns_test_notifcation_name_prefix}-queue"
  fifo_queue                 = false
  kms_master_key_id          = aws_kms_key.mns_outbound_events.arn
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
