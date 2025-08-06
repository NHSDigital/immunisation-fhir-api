resource "aws_sqs_queue" "id_sync_queue" {
  name                        = "${local.short_prefix}-id-sync-queue"
  kms_master_key_id           = data.aws_kms_key.existing_id_sync_sqs_encryption_key.arn
  visibility_timeout_seconds  = 360
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.id_sync_dlq.arn
    maxReceiveCount     = 4
  })
}

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
