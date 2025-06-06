locals {
  redis_sync_dir = abspath("${path.root}/../redis_sync")
  redis_sync_files = fileset(local.redis_sync_dir, "**")
  redis_sync_dir_sha = sha1(join("", [for f in local.redis_sync_files : filesha1("${local.redis_sync_dir}/${f}")]))
  function_name = "redis_sync"
  dlq_name = "redis_sync-dlq"
  sns_name = "redis_sync-sns"
}

resource "aws_iam_role" "redis_sync_lambda_role" {
  name               = "${local.short_prefix}-${local.function_name}-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "redis_sync_lambda_role_policy" {
  name   = "${local.prefix}-${local.function_name}-policy"
  role   = aws_iam_role.redis_sync_lambda_role.id
  policy = data.aws_iam_policy_document.redis_sync_policy_document.json
}

data "archive_file" "redis_sync_lambda_zip" {
  type        = "zip"
  source_dir  = local.redis_sync_dir
  output_path = "${path.module}/build/redis_sync_lambda.zip"
}

resource "aws_lambda_function" "redis_sync_lambda" {
  function_name = "${local.short_prefix}-${local.function_name}"
  role          = aws_iam_role.redis_sync_lambda_role.arn
  handler       = "redis_sync.sync_handler" # Update as appropriate
  runtime       = "python3.11"
  filename      = data.archive_file.redis_sync_lambda_zip.output_path
  source_code_hash = data.archive_file.redis_sync_lambda_zip.output_base64sha256
  architectures = ["x86_64"]

  environment {
    variables = {
      DELTA_TABLE_NAME     = aws_dynamodb_table.delta-dynamodb-table.name
      AWS_SQS_QUEUE_URL    = aws_sqs_queue.dlq.id
      SOURCE               = "IEDS"
      SPLUNK_FIREHOSE_NAME = module.splunk.firehose_stream_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.redis_sync_lambda
  ]
}

resource "aws_cloudwatch_log_group" "redis_sync_lambda" {
  name              = "/aws/lambda/${local.short_prefix}-${local.function_name}"
  retention_in_days = 30
}

resource "aws_lambda_event_source_mapping" "redis_sync_trigger" {
  event_source_arn  = aws_dynamodb_table.events-dynamodb-table.stream_arn
  function_name     = aws_lambda_function.redis_sync_lambda.function_name
  starting_position = "TRIM_HORIZON"
  destination_config {
    on_failure {
      destination_arn = aws_sns_topic.redis_sync_sns.arn
    }
  }
  maximum_retry_attempts = 0
}

resource "aws_sqs_queue" "dlq" {
  name = "${local.short_prefix}-${local.dlq_name}"
}

resource "aws_sns_topic" "redis_sync_sns" {
  name = "${local.short_prefix}-${local.sns_name}"
}

data "aws_iam_policy_document" "redis_sync_policy_document" {
  source_policy_documents = [
    templatefile("${local.policy_path}/dynamodb.json", {
      "dynamodb_table_name" : aws_dynamodb_table.delta-dynamodb-table.name
    }),
    templatefile("${local.policy_path}/dynamodb_stream.json", {
      "dynamodb_table_name" : aws_dynamodb_table.events-dynamodb-table.name
    }),
    templatefile("${local.policy_path}/aws_sqs_queue.json", {
      "aws_sqs_queue_name" : aws_sqs_queue.dlq.name
    }),
    templatefile("${local.policy_path}/dynamo_key_access.json", {
      "dynamo_encryption_key" : data.aws_kms_key.existing_dynamo_encryption_key.arn
    }),
    templatefile("${local.policy_path}/aws_sns_topic.json", {
      "aws_sns_topic_name" : aws_sns_topic.redis_sync_sns.name
    }),
    templatefile("${local.policy_path}/log_kinesis.json", {
      "kinesis_stream_name" : module.splunk.firehose_stream_name
    }),
    templatefile("${local.policy_path}/log.json", {}),
  ]
}