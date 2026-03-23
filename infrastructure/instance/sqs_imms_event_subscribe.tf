resource "aws_sqs_queue" "imms_subscribe_queue" {
  name                       = "imms-${local.resource_scope}-imms-subscribe-queue"
  kms_master_key_id          = data.aws_kms_key.imms_subscribe_sqs_encryption_key.arn
  visibility_timeout_seconds = 250
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.imms_subscribe_dlq.arn
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "imms_subscribe_dlq" {
  name = "imms-${local.resource_scope}-imms-subscribe-dlq"
}

resource "aws_sqs_queue_redrive_allow_policy" "imms_subscribe_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.imms_subscribe_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.imms_subscribe_queue.arn]
  })
}