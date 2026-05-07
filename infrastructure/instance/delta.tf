locals {
  delta_lambda_name = "${local.short_prefix}-delta-lambda"
  dlq_name          = "delta-dlq"
}

data "aws_iam_policy_document" "delta_policy_document" {
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
    templatefile("${local.policy_path}/log_kinesis.json", {
      "kinesis_stream_name" : module.splunk.firehose_stream_name
    }),
    templatefile("${local.policy_path}/log.json", {}),
  ]
}

resource "aws_iam_role" "delta_lambda_role" {
  name = "${local.delta_lambda_name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid    = "",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_role_policy" {
  name   = "${local.prefix}-delta-policy"
  role   = aws_iam_role.delta_lambda_role.id
  policy = data.aws_iam_policy_document.delta_policy_document.json
}


resource "aws_lambda_function" "delta_sync_lambda" {
  function_name = local.delta_lambda_name
  role          = aws_iam_role.delta_lambda_role.arn
  package_type  = "Image"
  architectures = ["x86_64"]
  image_uri     = var.delta_backend_image_uri
  timeout       = 60

  environment {
    variables = {
      DELTA_TABLE_NAME     = aws_dynamodb_table.delta-dynamodb-table.name
      DELTA_TTL_DAYS       = 30
      AWS_SQS_QUEUE_URL    = aws_sqs_queue.dlq.id
      SOURCE               = "IEDS"
      SPLUNK_FIREHOSE_NAME = module.splunk.firehose_stream_name
      LOG_LEVEL            = "INFO"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.delta_lambda
  ]
}

resource "aws_sqs_queue" "dlq" {
  name = "${local.short_prefix}-${local.dlq_name}"
}

resource "aws_cloudwatch_log_group" "delta_lambda" {
  name              = "/aws/lambda/${local.delta_lambda_name}"
  retention_in_days = 30
}


resource "aws_cloudwatch_log_metric_filter" "delta_error_logs" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  name           = "${local.short_prefix}-DeltaErrorLogsFilter"
  pattern        = "{ $.level = \"ERROR\" }"
  log_group_name = aws_cloudwatch_log_group.delta_lambda.name

  metric_transformation {
    name      = "${local.short_prefix}-DeltaErrorLogs"
    namespace = "${local.short_prefix}-DeltaLambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "delta_error_alarm" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name          = "${local.delta_lambda_name}-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.short_prefix}-DeltaErrorLogs"
  namespace           = "${local.short_prefix}-DeltaLambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in the delta Lambda function"
  alarm_actions       = [data.aws_sns_topic.imms_system_alert_errors.arn]
  treat_missing_data  = "notBreaching"
}
