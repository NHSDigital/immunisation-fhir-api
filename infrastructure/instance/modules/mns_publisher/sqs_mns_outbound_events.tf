resource "aws_sqs_queue" "mns_outbound_events" {
  name                       = "${var.mns_publisher_resource_name_prefix}-queue"
  fifo_queue                 = false
  kms_master_key_id          = aws_kms_key.mns_outbound_events.arn
  visibility_timeout_seconds = 180
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.mns_outbound_events_dlq.arn
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "mns_outbound_events_dlq" {
  name              = "${var.mns_publisher_resource_name_prefix}-dead-letter-queue"
  kms_master_key_id = aws_kms_key.mns_outbound_events.arn
}

resource "aws_sqs_queue_redrive_allow_policy" "terraform_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.mns_outbound_events_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.mns_outbound_events.arn]
  })
}

data "aws_iam_policy_document" "mns_outbound_events_sqs_policy" {
  statement {
    sid    = "mns-outbound-allow-eb-pipe-access"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.mns_outbound_events_eb_pipe.arn]
    }

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.mns_outbound_events.arn
    ]
  }
}

resource "aws_sqs_queue_policy" "mns_outbound_events_sqs" {
  queue_url = aws_sqs_queue.mns_outbound_events.id
  policy    = data.aws_iam_policy_document.mns_outbound_events_sqs_policy.json
}
