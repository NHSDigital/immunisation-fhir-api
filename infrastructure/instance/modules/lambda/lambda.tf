module "lambda_function_container_image" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.0.1"

  create_role                       = false
  lambda_role                       = aws_iam_role.lambda_role.arn
  function_name                     = "${var.short_prefix}_${var.function_name}"
  handler                           = "${var.function_name}_handler.${var.function_name}_handler"
  cloudwatch_logs_retention_in_days = 30
  create_package                    = false
  image_uri                         = var.image_uri
  package_type                      = "Image"
  architectures                     = ["x86_64"]
  timeout                           = 6

  vpc_subnet_ids         = var.vpc_subnet_ids
  vpc_security_group_ids = var.vpc_security_group_ids

  # A JWT encode took 7 seconds at default memory size of 128 and 0.8 seconds at 1024.
  # 2048 gets it down to around 0.5 but since Lambda is charged at GB * ms then it costs more for minimal benefit.
  memory_size = 1024

  environment_variables = var.environment_variables
  image_config_command  = ["${var.function_name}_handler.${var.function_name}_handler"]
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

  log_group_name = module.lambda_function_container_image.lambda_cloudwatch_log_group_name

  metric_transformation {
    name      = "max-memory-used"
    namespace = var.short_prefix
    value     = "$18"
  }
}

resource "aws_cloudwatch_log_metric_filter" "fhir_api_error_logs" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  name           = "${local.short_prefix}_${var.function_name}-ErrorLogsFilter"
  pattern        = "{ $.operation_outcome.status = \"500\" || $.operation_outcome.status = \"403\" }"
  log_group_name = module.lambda_function_container_image.lambda_cloudwatch_log_group_name

  metric_transformation {
    name      = "${local.short_prefix}_${var.function_name}-ApiErrorLogs"
    namespace = "${local.short_prefix}-_${var.function_name}-Lambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "fhir_api_error_alarm" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name          = "${local.short_prefix}_${var.function_name}-lambda-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.short_prefix}_${var.function_name}-ErrorLogs"
  namespace           = "${local.short_prefix}_${var.function_name}-Lambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in fhir api Lambda function"
  alarm_actions       = var.aws_sns_topic != null ? [var.aws_sns_topic] : []
  treat_missing_data  = "notBreaching"
}
