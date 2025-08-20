resource "aws_cloudwatch_event_rule" "batch_file_created" {
  name        = "${local.short_prefix}-data-source-batch-file-created"
  description = "Batch file was added to the data sources S3 bucket"

  event_pattern = jsonencode({
    source = [
        "aws.s3"
    ],
    detail-type = [
      "Object Created"
    ],
    detail = {
        bucket = {
            name = ["${aws_s3_bucket.batch_data_source_bucket.bucket}"]
        },
        object = {
            key = [
                {
                    anything-but = {
                        prefix = "archive/"
                    }
                },
                {
                    anything-but = {
                        prefix = "processing/"
                    }
                }
            ]
        }
    }
  })
}

resource "aws_cloudwatch_event_target" "batch_file_created_sqs_queue" {
  rule = aws_cloudwatch_event_rule.batch_file_created.name
  arn  = aws_sqs_queue.batch_file_created_queue.arn

  sqs_target {
    message_group_id = "new_batch_file"
  }
}
