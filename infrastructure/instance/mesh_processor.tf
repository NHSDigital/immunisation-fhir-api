locals {
  mesh_processor_lambda_name = "${local.short_prefix}-mesh-processor-lambda"
  # This should match the prefix used in the global Terraform
  mesh_module_prefix = "imms-${var.environment}-mesh"
}

data "aws_s3_bucket" "mesh" {
  count = var.create_mesh_processor ? 1 : 0

  bucket = local.mesh_module_prefix
}

data "aws_kms_key" "mesh" {
  count = var.create_mesh_processor ? 1 : 0

  key_id = "alias/${local.mesh_module_prefix}"
}

# IAM Role for Lambda
resource "aws_iam_role" "mesh_processor_lambda_exec_role" {
  count = var.create_mesh_processor ? 1 : 0

  name = "${local.mesh_processor_lambda_name}-exec-role"
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
resource "aws_iam_policy" "mesh_processor_lambda_exec_policy" {
  count = var.create_mesh_processor ? 1 : 0

  name = "${local.mesh_processor_lambda_name}-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.mesh_processor_lambda_name}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:CopyObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.batch_data_source_bucket.arn,
          "${aws_s3_bucket.batch_data_source_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:CopyObject",
          "s3:DeleteObject"
        ]
        Resource = [
          data.aws_s3_bucket.mesh[0].arn,
          "${data.aws_s3_bucket.mesh[0].arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "mesh_processor_lambda_kms_access_policy" {
  count = var.create_mesh_processor ? 1 : 0

  name        = "${local.mesh_processor_lambda_name}-kms-policy"
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
          data.aws_kms_key.mesh[0].arn
        ]
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_exec_policy_attachment" {
  count = var.create_mesh_processor ? 1 : 0

  role       = aws_iam_role.mesh_processor_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mesh_processor_lambda_exec_policy[0].arn
}


# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_kms_policy_attachment" {
  count = var.create_mesh_processor ? 1 : 0

  role       = aws_iam_role.mesh_processor_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mesh_processor_lambda_kms_access_policy[0].arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "mesh_file_converter_lambda" {
  count = var.create_mesh_processor ? 1 : 0

  function_name = local.mesh_processor_lambda_name
  role          = aws_iam_role.mesh_processor_lambda_exec_role[0].arn
  package_type  = "Image"
  image_uri     = var.mesh_processor_image_uri
  architectures = ["x86_64"]
  timeout       = 900
  memory_size   = 1024

  environment {
    variables = {
      ACCOUNT_ID              = var.immunisation_account_id
      DESTINATION_BUCKET_NAME = aws_s3_bucket.batch_data_source_bucket.bucket
    }
  }
}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "mesh_s3_invoke_permission" {
  count = var.create_mesh_processor ? 1 : 0

  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mesh_file_converter_lambda[0].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = data.aws_s3_bucket.mesh[0].arn
}

resource "aws_s3_bucket_notification" "mesh_datasources_lambda_notification" {
  count = var.create_mesh_processor ? 1 : 0

  bucket = data.aws_s3_bucket.mesh[0].bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.mesh_file_converter_lambda[0].arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "inbound/"
  }

  depends_on = [
    aws_lambda_permission.mesh_s3_invoke_permission
  ]
}

resource "aws_cloudwatch_log_group" "mesh_file_converter_log_group" {
  count = var.create_mesh_processor ? 1 : 0

  name              = "/aws/lambda/${local.mesh_processor_lambda_name}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_metric_filter" "mesh_processor_error_logs" {
  count = var.create_mesh_processor && var.error_alarm_notifications_enabled ? 1 : 0

  name           = "${local.short_prefix}-MeshProcessorErrorLogsFilter"
  pattern        = "%\\[ERROR\\]%"
  log_group_name = aws_cloudwatch_log_group.mesh_file_converter_log_group[0].name

  metric_transformation {
    name      = "${local.short_prefix}-MeshProcessorErrorLogs"
    namespace = "${local.short_prefix}-MeshProcessorLambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "mesh_processor_error_alarm" {
  count = var.create_mesh_processor && var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name          = "${local.mesh_processor_lambda_name}-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.short_prefix}-MeshProcessorErrorLogs"
  namespace           = "${local.short_prefix}-MeshProcessorLambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in the mesh processor Lambda function"
  alarm_actions       = [data.aws_sns_topic.imms_system_alert_errors.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "mesh_processor_no_lambda_invocation_alarm" {
  count = var.create_mesh_processor && var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name        = "imms-${local.resource_scope}-mesh-processor-no-lambda-invocation"
  alarm_description = "Triggers when the MESH Processor Lambda has no invocations for the configured time window."

  metric_name = "Invocations"
  namespace   = "AWS/Lambda"
  statistic   = "Sum"
  period      = var.mesh_no_invocation_period_seconds

  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  dimensions = {
    FunctionName = aws_lambda_function.mesh_file_converter_lambda[0].function_name
  }

  alarm_actions = [data.aws_sns_topic.imms_system_alert_errors.arn]
}
