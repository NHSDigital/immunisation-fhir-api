locals {
  # There is no blue-green split in our dev environment but we still want to monitor internal-dev and internal-qa
  sub_environments_map = {
    dev     = ["internal-dev", "internal-qa"],
    preprod = ["int-blue", "int-green"],
    prod    = ["blue", "green"],
  }
  errors_colour_code = "#d62728" # red

  # API Lambda
  api_lambdas = flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_search_imms"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_create_imms"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_get_imms"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_update_imms"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_delete_imms"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_not_found"],
  ])

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
  batch_lambdas = flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-batch-processor-filter-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ack-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-forwarding-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-filenameproc-lambda"],
  ])

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
  ancillary_lambdas = flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-id-sync-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-delta-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_get_status"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-redis-sync-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-mesh-processor-lambda" if var.environment != "dev"],
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
  # We only have tables by sub-environment in dev
  dynamodb_tables = compact([
    "imms-${var.environment == "dev" ? "internal-dev" : var.environment}-delta",
    "imms-${var.environment == "dev" ? "internal-dev" : var.environment}-imms-events",
    "immunisation-batch-${var.environment == "dev" ? "internal-dev" : var.environment}-audit-table",
    var.environment == "dev" ? "imms-internal-qa-delta" : "",
    var.environment == "dev" ? "imms-internal-qa-imms-events" : "",
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
  kinesis_metrics = [for sub_env in local.sub_environments_map[var.environment] :
    ["AWS/Kinesis", "IncomingBytes", "StreamName", "imms-${sub_env}-processingdata-stream"]
  ]

  # SQS
  sqs_queues = flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ack-metadata-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-batch-file-created-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-delta-dlq"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-metadata-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : (var.environment == "dev" ? "imms-${sub_env}-id-sync-dlq" : "imms-${var.environment}-id-sync-dlq")],
    [for sub_env in local.sub_environments_map[var.environment] : (var.environment == "dev" ? "imms-${sub_env}-id-sync-queue" : "imms-${var.environment}-id-sync-queue")],
  ])
  sqs_queue_metrics = [for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", queue, { region : var.aws_region }]]

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
  # Alarms are turned off in internal-qa as testing could cause unnecessary noise
  dev_alarms = [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-internal-dev${alarm}"]
  non_dev_alarms = flatten([for sub_env in local.sub_environments_map[var.environment] :
  [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${sub_env}${alarm}"] if var.environment != "dev"])
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
          "markdown" : "### Ancillaries"
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
          "region" : var.aws_region,
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
        "y" : 56,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "# Alarms"
        }
      },
      {
        "type" : "alarm",
        "x" : 0,
        "y" : 57,
        "width" : 24,
        "height" : var.environment == "dev" ? 5 : 10,
        "properties" : {
          "alarms" : local.alarms_properties
        }
      }
    ]
    }
  )
}
