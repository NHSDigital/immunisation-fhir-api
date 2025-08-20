data "aws_iam_policy_document" "batch_file_created_queue_policy" {
  statement {
    effect = "Allow"

		principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions   = ["sqs:SendMessage"]
    resources = [
			"arn:aws:sqs:eu-west-2:${var.immunisation_account_id}:${local.short_prefix}-batch-file-created-queue.fifo"
		]
  }
}

# FIFO SQS Queue - targetted by Event Bridge for new objects created in the data-sources S3 bucket
resource "aws_sqs_queue" "batch_file_created_queue" {
  name                        = "${local.short_prefix}-batch-file-created-queue.fifo"
	policy                      = data.aws_iam_policy_document.batch_file_created_queue_policy.json
  fifo_queue                  = true
  content_based_deduplication = true # Optional, helps with deduplication
  visibility_timeout_seconds  = 420
}
