# FIFO SQS Queue
resource "aws_sqs_queue" "supplier_fifo_queue" {
 name                      = "${local.short_prefix}-metadata-queue.fifo"# Must end with .fifo
 fifo_queue                = true
 content_based_deduplication = true # Optional, helps with deduplication
 visibility_timeout_seconds = 60
}

locals {
  existing_sqs_arns = aws_sqs_queue.supplier_fifo_queue.name
}
