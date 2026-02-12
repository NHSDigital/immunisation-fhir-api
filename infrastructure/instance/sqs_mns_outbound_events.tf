resource "aws_sqs_queue" "mns_outbound_events" {
  name                       = "${local.resource_scope}-mns-outbound-events"
  fifo_queue                 = false
  visibility_timeout_seconds = 180
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

# TODO - (follow on once we have basics set up so Lambda coding can start)
# Add KMS encryption to queue, add DLQ and redrive
