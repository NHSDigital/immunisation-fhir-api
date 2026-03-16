module "lambda_function_zip" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.0.1"

  create_role                       = false
  lambda_role                       = aws_iam_role.lambda_role.arn
  function_name                     = "${var.short_prefix}_${var.function_name}"
  handler                           = "${var.function_name}_handler.${var.function_name}_handler"
  runtime                           = "python3.11"
  cloudwatch_logs_retention_in_days = 30
  package_type                      = "Zip"
  architectures                     = ["x86_64"]
  timeout                           = 6
  store_on_s3                       = true
  s3_bucket                         = var.artifact_s3_bucket
  s3_prefix                         = "lambda-artifacts/${var.short_prefix}_${var.function_name}"
  build_in_docker                   = true
  hash_extra                        = var.source_hash
  trigger_on_package_timestamp      = false

  source_path = [
    {
      path = "${var.lambda_source_dir}/src"
    },
    {
      path          = var.shared_source_dir
      prefix_in_zip = "common"
    },
    {
      path           = var.lambda_source_dir
      poetry_install = true
      patterns = [
        "pyproject.toml",
        "poetry.lock"
      ]
    }
  ]

  vpc_subnet_ids         = var.vpc_subnet_ids
  vpc_security_group_ids = var.vpc_security_group_ids

  # A JWT encode took 7 seconds at default memory size of 128 and 0.8 seconds at 1024.
  # 2048 gets it down to around 0.5 but since Lambda is charged at GB * ms then it costs more for minimal benefit.
  memory_size = 1024

  environment_variables = var.environment_variables
}

resource "aws_cloudwatch_metric_alarm" "memory_alarm" {
  alarm_name                = "${var.short_prefix}_${var.function_name} memory alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = 1
  metric_name               = aws_cloudwatch_log_metric_filter.max_memory_used_metric.metric_transformation[0].name
  namespace                 = aws_cloudwatch_log_metric_filter.max_memory_used_metric.metric_transformation[0].namespace
  period                    = 600
  statistic                 = "Maximum"
  threshold                 = 256
  alarm_description         = "This metric monitors Lambda memory usage"
  insufficient_data_actions = []

}

resource "aws_cloudwatch_log_metric_filter" "max_memory_used_metric" {
  name    = "${var.short_prefix}_${var.function_name} max memory used"
  pattern = "[type=REPORT, ...]"

  log_group_name = module.lambda_function_zip.lambda_cloudwatch_log_group_name

  metric_transformation {
    name      = "max-memory-used"
    namespace = "${var.short_prefix}_${var.function_name}"
    value     = "$18"
  }
}

resource "aws_cloudwatch_log_metric_filter" "fhir_api_error_logs" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  name           = "${var.short_prefix}_${var.function_name}-ErrorLogsFilter"
  pattern        = "{ $.operation_outcome.status = \"500\" || $.operation_outcome.status = \"403\" }"
  log_group_name = module.lambda_function_zip.lambda_cloudwatch_log_group_name

  metric_transformation {
    name      = "${var.short_prefix}_${var.function_name}-ApiErrorLogs"
    namespace = "${var.short_prefix}_${var.function_name}-Lambda"
    value     = "1"
  }
}

data "aws_sns_topic" "fhir_api_errors" {
  name = "${var.environment}-fhir-api-errors"
}

resource "aws_cloudwatch_metric_alarm" "fhir_api_error_alarm" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name          = "${var.short_prefix}_${var.function_name}-lambda-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${var.short_prefix}_${var.function_name}-ApiErrorLogs"
  namespace           = "${var.short_prefix}_${var.function_name}-Lambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Triggers an alarm when 500 or 403 error responses are logged by the FHIR API Lambda function."
  alarm_actions       = [data.aws_sns_topic.fhir_api_errors.arn]
  treat_missing_data  = "notBreaching"
}
