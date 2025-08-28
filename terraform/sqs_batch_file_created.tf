# FIFO SQS Queue - targeted by Filename Processor Lambda function
resource "aws_sqs_queue" "batch_file_created" {
  name                        = "${local.short_prefix}-batch-file-created-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true # Optional, helps with deduplication
  visibility_timeout_seconds  = 60 # TODO - discuss and refine this + DDB TTL
}
