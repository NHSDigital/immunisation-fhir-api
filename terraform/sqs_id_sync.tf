# FIFO SQS Queue
resource "aws_sqs_queue" "id_sync_queue" {
  name                        = "${local.short_prefix}-id-sync-queue.fifo" # Must end with .fifo
  fifo_queue                  = true
  content_based_deduplication = true # Optional, helps with deduplication
  visibility_timeout_seconds  = 60
}
