locals {
  non_dev_blue       = var.environment == "prod" ? "blue" : "int-blue"
  non_dev_green      = var.environment == "prod" ? "green" : "int-green"
  errors_colour_code = "#d62728" # red

  # API Lambda
  api_lambdas = [
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_search_imms",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_search_imms",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_create_imms",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_create_imms",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_get_imms",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_get_imms",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_update_imms",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_update_imms",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_delete_imms",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_delete_imms",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_not_found",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_not_found"
  ]

  api_lambda_invocations_metrics            = [for lambda in local.api_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { region : var.aws_region }]]
  api_lambda_errors_metrics                 = [for lambda in local.api_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region }]]
  api_lambda_invocations_and_errors_metrics = concat(local.api_lambda_invocations_metrics, local.api_lambda_errors_metrics)
  api_lambda_duration_metrics = concat(
    [[{ expression : "AVG(METRICS())", label : "Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
    [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "m${i + 1}", region : var.aws_region }]],
  )
  api_lambda_concurrent_execution_metrics = [for lambda in local.api_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { region : var.aws_region }]]
  api_lambda_total_errors_metrics = concat(
    [[{ expression : "SUM(METRICS())", label : "API Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
    [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region, id : "m${i + 1}", visible : false }]]
  )

  # Batch Lambda
  batch_lambdas = [
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-batch-processor-filter-lambda",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-batch-processor-filter-lambda",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-ack-lambda",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-ack-lambda",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-forwarding-lambda",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-forwarding-lambda",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-filenameproc-lambda",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-filenameproc-lambda"
  ]

  batch_lambda_invocations_metrics            = [for lambda in local.batch_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { region : var.aws_region }]]
  batch_lambda_errors_metrics                 = [for lambda in local.batch_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region }]]
  batch_lambda_invocations_and_errors_metrics = concat(local.batch_lambda_invocations_metrics, local.batch_lambda_errors_metrics)
  batch_lambda_duration_metrics = concat(
    [[{ expression : "AVG(METRICS())", label : "Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
    [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "m${i + 1}", region : var.aws_region }]]
  )
  batch_lambda_concurrent_execution_metrics = [for lambda in local.batch_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { region : var.aws_region }]]
  batch_lambda_total_errors_metrics = concat(
    [[{ expression : "SUM(METRICS())", label : "API Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
    [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region, id : "m${i + 1}", visible : false }]]
  )

  # Ancillary Lambda
  ancillary_lambdas = compact([
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-id-sync-lambda",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-id-sync-lambda",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-delta-lambda",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-delta-lambda",
    "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}_get_status",
    "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}_get_status",
    var.environment != "dev" ? "imms-${local.non_dev_blue}-mesh-processor-lambda" : "",
    var.environment != "dev" ? "imms-${local.non_dev_green}-mesh-processor-lambda" : "",
    var.environment != "dev" ? "imms-${local.non_dev_blue}-redis-sync-lambda" : "",
    var.environment != "dev" ? "imms-${local.non_dev_green}-redis-sync-lambda" : "",
  ])

  ancillary_lambda_invocations_metrics            = [for lambda in local.ancillary_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { region : var.aws_region }]]
  ancillary_lambda_errors_metrics                 = [for lambda in local.ancillary_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region }]]
  ancillary_lambda_invocations_and_errors_metrics = concat(local.ancillary_lambda_invocations_metrics, local.ancillary_lambda_errors_metrics)
  ancillary_lambda_duration_metrics = concat(
    [[{ expression : "AVG(METRICS())", label : "Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
    [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "m${i + 1}", region : var.aws_region }]]
  )
  ancillary_lambda_concurrent_execution_metrics = [for lambda in local.ancillary_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { region : var.aws_region }]]
  ancillary_lambda_total_errors_metrics = concat(
    [[{ expression : "SUM(METRICS())", label : "API Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
    [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region, id : "m${i + 1}", visible : false }]]
  )

  # DynamoDB
  dynamodb_tables = compact([
    "imms-${var.environment == "dev" ? "internal-dev" : var.environment}-delta",
    var.environment == "dev" ? "imms-internal-qa-delta" : "",
    "imms-${var.environment == "dev" ? "internal-dev" : var.environment}-imms-events",
    var.environment == "dev" ? "imms-internal-qa-imms-events" : "",
    "immunisation-batch-${var.environment == "dev" ? "internal-dev" : var.environment}-audit-table",
    var.environment == "dev" ? "imms-internal-qa-audit-table" : "",
  ])

  dynamodb_getitems_metrics      = [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "GetItem", { region : var.aws_region }]]
  dynamodb_query_metrics         = [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "Query", { region : var.aws_region }]]
  dynamodb_read_metrics          = concat(local.dynamodb_getitems_metrics, local.dynamodb_query_metrics)
  dynamodb_read_capacity_metrics = [for table in local.dynamodb_tables : ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table]]

  dynamodb_putitems_metrics       = [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "PutItem", { region : var.aws_region }]]
  dynamodb_updateitem_metrics     = [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "UpdateItem", { region : var.aws_region }]]
  dynamodb_write_metrics          = concat(local.dynamodb_putitems_metrics, local.dynamodb_updateitem_metrics)
  dynamodb_write_capacity_metrics = [for table in local.dynamodb_tables : ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", table]]

  # Kinesis
  kinesis_metrics = [
    ["AWS/Kinesis", "IncomingBytes", "StreamName", "imms-${var.environment == "dev" ? "internal-dev" : local.non_dev_blue}-processingdata-stream"],
    ["AWS/Kinesis", "IncomingBytes", "StreamName", "imms-${var.environment == "dev" ? "internal-qa" : local.non_dev_green}-processingdata-stream"],
  ]

  # SQS
  sqs_queues = [
    "ack-metadata-queue.fifo",
    "batch-file-created-queue.fifo",
    "delta-dlq",
    "metadata-queue.fifo",
    "id-sync-dlq",
    "id-sync-queue"
  ]
  internal_dev_sqs_queue_metrics = [for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", "imms-internal-dev-${queue}", { region : var.aws_region }]]
  internal_qa_sqs_queue_metrics  = [for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", "imms-internal-qa-${queue}", { region : var.aws_region }]]
  dev_sqs_queue_metrics          = concat(local.internal_dev_sqs_queue_metrics, local.internal_qa_sqs_queue_metrics)
  blue_sqs_queue_metrics         = [for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", queue == "id-sync-dlq" || queue == "id-sync-queue" ? "imms-${var.environment}-${queue}" : "imms-${local.non_dev_blue}-${queue}", { region : var.aws_region }]]
  green_sqs_queue_metrics        = [for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", "imms-${local.non_dev_green}-${queue}", { region : var.aws_region }] if queue != "id-sync-dlq" || queue != "id-sync-queue"]
  non_dev_sqs_queue_metrics      = concat(local.blue_sqs_queue_metrics, local.green_sqs_queue_metrics)
  sqs_queue_metrics              = var.environment == "dev" ? local.dev_sqs_queue_metrics : local.non_dev_sqs_queue_metrics

  # Alarms
  alarms = [
    "_create_imms-lambda-error",
    "_create_imms memory alarm",
    "_get_imms-lambda-error",
    "_get_imms memory alarm",
    "_get_status memory alarm",
    "_get_status-lambda-error",
    "_search_imms-lambda-error",
    "_search_imms memory alarm",
    "_update_imms-lambda-error",
    "_update_imms memory alarm",
    "_delete_imms-lambda-error",
    "_delete_imms memory alarm",
    "-record-processor-task-error",
    "-file-name-processor-lambda-error",
    "-batch-processor-filter-lambda-error",
    "-id-sync-lambda-error",
    "-redis-sync-lambda-error",
    "-delta-lambda-error",
    "_not_found-lambda-error",
    "_not_found memory alarm"
  ]
  dev_alarms        = [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-internal-dev${alarm}"]
  blue_alarms       = [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${local.non_dev_blue}${alarm}"]
  green_alarms      = [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${local.non_dev_green}${alarm}"]
  non_dev_alarms    = concat(local.blue_alarms, local.green_alarms)
  alarms_properties = var.environment == "dev" ? local.dev_alarms : local.non_dev_alarms
}

resource "aws_cloudwatch_dashboard" "imms-metrics-dashboard" {
  dashboard_name = "imms-metrics-dashboard-${var.environment}"
  dashboard_body = jsonencode({
    "widgets" : [
      {
        "type" : "text",
        "x" : 0,
        "y" : 0,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "# Core Health Metrics"
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 1,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "## Lambda"
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 2,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "### Overview"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 3,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/Lambda", "Invocations", { region : var.aws_region }],
            [".", "Errors", { color : local.errors_colour_code, region : var.aws_region }],
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "Invocations & Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 3,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/Lambda",
              "Duration",
              { region : var.aws_region, color : "#ffbb78" }
            ]
          ],
          "view" : "timeSeries",
          "stacked" : true,
          "region" : var.aws_region,
          "title" : "Duration",
          "period" : 300,
          "stat" : "Average"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 3,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/Lambda",
              "ConcurrentExecutions",
              { color : "#2ca02c", region : var.aws_region }
            ]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ConcurrentExecutions"
        }
      },
      {
        "type" : "metric",
        "x" : 18,
        "y" : 3,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : [
            [
              "AWS/Lambda",
              "Errors",
              { region : var.aws_region, color : local.errors_colour_code }
            ]
          ],
          "sparkline" : true,
          "view" : "singleValue",
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 9,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "### API"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 10,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.api_lambda_invocations_and_errors_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "Invocations & Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 10,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.api_lambda_duration_metrics
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "Duration",
          "period" : 300,
          "stat" : "Average"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 10,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.api_lambda_concurrent_execution_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ConcurrentExecutions"
        }
      },
      {
        "type" : "metric",
        "x" : 18,
        "y" : 10,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : local.api_lambda_total_errors_metrics,
          "sparkline" : true,
          "view" : "singleValue",
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 16,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "### Batch"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 17,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.batch_lambda_invocations_and_errors_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "Invocations & Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 17,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.batch_lambda_duration_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "Duration",
          "period" : 300,
          "stat" : "Average"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 17,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.batch_lambda_concurrent_execution_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ConcurrentExecutions"
        }
      },
      {
        "type" : "metric",
        "x" : 18,
        "y" : 17,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : local.batch_lambda_total_errors_metrics,
          "sparkline" : true,
          "view" : "singleValue",
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 23,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "### Ancilliaries"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 24,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.ancillary_lambda_invocations_and_errors_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "Invocations & Errors"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 24,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.ancillary_lambda_duration_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "Duration",
          "period" : 300,
          "stat" : "Average"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 24,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.ancillary_lambda_concurrent_execution_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ConcurrentExecutions"
        }
      },
      {
        "type" : "metric",
        "x" : 18,
        "y" : 24,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : local.ancillary_lambda_total_errors_metrics,
          "sparkline" : true,
          "view" : "singleValue",
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 30,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "## DynamoDB"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 31,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.dynamodb_read_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "period" : 300,
          "title" : "Successful Read Requests (count)",
          "stat" : "SampleCount",
          "yAxis" : {
            "left" : {
              "label" : ""
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 31,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.dynamodb_read_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "period" : 300,
          "title" : "Successful Read Requests (latency)",
          "stat" : "Average"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 31,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.dynamodb_read_capacity_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "ConsumedReadCapacityUnits"
        }
      },
      {
        "type" : "metric",
        "x" : 18,
        "y" : 31,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/DynamoDB",
              "UserErrors",
              "Operation",
              "GetRecords",
              { color : local.errors_colour_code, region : var.aws_region }
            ]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 37,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.dynamodb_write_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "period" : 300,
          "title" : "Successful Write Requests (count)",
          "stat" : "SampleCount",
          "yAxis" : {
            "left" : {
              "label" : ""
            }
          }
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 37,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.dynamodb_write_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "period" : 300,
          "title" : "Successful Write Requests (latency)",
          "stat" : "Average"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 37,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.dynamodb_write_capacity_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "ConsumedWriteCapacityUnits"
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 43,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "## Other"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 44,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : [["AWS/ApiGateway", "DataProcessed"]],
          "region" : var.aws_region,
          "title" : "ApiGateway - DataProcessed Across All APIs"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 44,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : local.kinesis_metrics,
          "region" : var.aws_region,
          "title" : "Kinesis - IncomingBytes"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 44,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : local.sqs_queue_metrics,
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "SQS Queues - NumberOfMessagesSent",
          "period" : 300,
          "stat" : "Sum"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 50,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : [
            ["AWS/ElastiCache", "CacheHits", "CacheClusterId", "immunisation-redis-cluster", "CacheNodeId", "0001"]
          ],
          "region" : "eu-west-2",
          "title" : "ElastiCache - CacheHits"
          "period" : 300,
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 50,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "immunisation-redis-cluster", "CacheNodeId", "0001"]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "ElastiCache - CPUUtilization",
          "period" : 300,
          "stat" : "Average"
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 50,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "# Alarms"
        }
      },
      {
        "type" : "alarm",
        "x" : 0,
        "y" : 51,
        "width" : 24,
        "height" : var.environment == "dev" ? 4 : 8,
        "properties" : {
          "alarms" : local.alarms_properties
        }
      }
    ]
    }
  )
}
