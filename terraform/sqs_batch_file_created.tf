# FIFO SQS Queue - targeted by Filename Processor Lambda function
resource "aws_sqs_queue" "batch_file_created" {
  name                        = "${local.short_prefix}-batch-file-created-queue.fifo"
  policy                      = data.aws_iam_policy_document.batch_file_created_queue_policy.json
  fifo_queue                  = true
  content_based_deduplication = true # Optional, helps with deduplication
  visibility_timeout_seconds  = 900 # TODO - discuss and refine both this, max receives and DLQ
}
