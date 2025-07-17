# Standard SQS Queue

resource "aws_sqs_queue" "id_sync_queue" {
  name                        = "${local.short_prefix}-id-sync-queue"
  visibility_timeout_seconds  = 60
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.id_sync_dlq.arn
    maxReceiveCount     = 4
  })}

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
