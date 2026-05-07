locals {
  ack_lambda_name = "${local.short_prefix}-ack-lambda"
}

# IAM Role for Lambda
resource "aws_iam_role" "ack_lambda_exec_role" {
  name = "${local.ack_lambda_name}-exec-role"
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

# Policy for Lambda execution role
resource "aws_iam_policy" "ack_lambda_exec_policy" {
  name = "${local.ack_lambda_name}-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.ack_lambda_name}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:CopyObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.batch_data_source_bucket.arn,
          "${aws_s3_bucket.batch_data_source_bucket.arn}/*",
          aws_s3_bucket.batch_data_destination_bucket.arn,
          "${aws_s3_bucket.batch_data_destination_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.audit-table.arn,
          "${aws_dynamodb_table.audit-table.arn}/index/*",
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
      Resource = "arn:aws:sqs:${var.aws_region}:${var.immunisation_account_id}:${local.short_prefix}-ack-metadata-queue.fifo" },
      {
        "Effect" : "Allow",
        "Action" : [
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        "Resource" : "arn:aws:firehose:*:*:deliverystream/${module.splunk.firehose_stream_name}"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "ack_lambda_log_group" {
  name              = "/aws/lambda/${local.ack_lambda_name}"
  retention_in_days = 30
}

resource "aws_iam_policy" "ack_s3_kms_access_policy" {
  name        = "${local.short_prefix}-ack-s3-kms-policy"
  description = "Allow Lambda to decrypt environment variables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = [
          data.aws_kms_key.existing_s3_encryption_key.arn,
          data.aws_kms_key.existing_dynamo_encryption_key.arn
        ]
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_exec_policy_attachment" {
  role       = aws_iam_role.ack_lambda_exec_role.name
  policy_arn = aws_iam_policy.ack_lambda_exec_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_kms_policy_attachment" {
  role       = aws_iam_role.ack_lambda_exec_role.name
  policy_arn = aws_iam_policy.ack_s3_kms_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "ack_processor_lambda" {
  function_name = local.ack_lambda_name
  role          = aws_iam_role.ack_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = var.ack_backend_image_uri
  architectures = ["x86_64"]
  timeout       = 900
  memory_size   = 2048
  ephemeral_storage {
    size = 2048
  }

  environment {
    variables = {
      ACK_BUCKET_NAME      = aws_s3_bucket.batch_data_destination_bucket.bucket
      SPLUNK_FIREHOSE_NAME = module.splunk.firehose_stream_name
      SOURCE_BUCKET_NAME   = aws_s3_bucket.batch_data_source_bucket.bucket
      AUDIT_TABLE_NAME     = aws_dynamodb_table.audit-table.name
    }
  }

  reserved_concurrent_executions = local.is_temp ? -1 : 20
  depends_on = [
    aws_cloudwatch_log_group.ack_lambda_log_group
  ]
}

resource "aws_lambda_event_source_mapping" "sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.fifo_queue.arn
  function_name    = aws_lambda_function.ack_processor_lambda.arn
  batch_size       = 1 # VED-734 - forwarder lambda already sends a list of up to 100 messages in the body
  enabled          = true
}

resource "aws_cloudwatch_log_metric_filter" "ack_lambda_error_logs" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  name           = "${local.short_prefix}-AckLambdaErrorLogsFilter"
  pattern        = "%\\[ERROR\\]%"
  log_group_name = aws_cloudwatch_log_group.ack_lambda_log_group.name

  metric_transformation {
    name      = "${local.short_prefix}-AckLambdaErrorLogs"
    namespace = "${local.short_prefix}-AckLambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "ack_lambda_error_alarm" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name          = "${local.ack_lambda_name}-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.short_prefix}-AckLambdaErrorLogs"
  namespace           = "${local.short_prefix}-AckLambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in the ack Lambda function"
  alarm_actions       = [data.aws_sns_topic.imms_system_alert_errors.arn]
  treat_missing_data  = "notBreaching"
}
