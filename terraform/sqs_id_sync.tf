# Standard SQS Queue

resource "aws_sqs_queue" "id_sync_queue" {
  name                        = "${local.short_prefix}-id-sync-queue"
  kms_master_key_id           = aws_kms_alias.id_sync_sqs_encryption.name
  visibility_timeout_seconds  = 60
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.id_sync_dlq.arn
    maxReceiveCount     = 4
  })
}

# DLQ for id-sync-queue

resource "aws_sqs_queue" "id_sync_dlq" {
  name = "${local.short_prefix}-id-sync-dlq"
}

resource "aws_sqs_queue_redrive_allow_policy" "id_sync_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.id_sync_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.id_sync_queue.arn]
  })
}

# IAM policy.
# TODO: this is currently a global allow policy.
# Refine this to allow receive from our lambda, and send from MNS

data "aws_iam_policy_document" "id_sync_sqs_policy" {
  statement {
    sid    = "id-sync-queue SQS statement"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage"
    ]
    resources = [
      aws_sqs_queue.id_sync_queue.arn
    ]
  }
}

resource "aws_sqs_queue_policy" "id_sync_sqs_policy" {
  queue_url = aws_sqs_queue.id_sync_queue.id
  policy    = data.aws_iam_policy_document.id_sync_sqs_policy.json
}
