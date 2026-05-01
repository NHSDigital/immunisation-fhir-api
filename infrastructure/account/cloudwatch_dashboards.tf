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

  # Batch Lambda
  batch_lambdas = flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-batch-processor-filter-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ack-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-forwarding-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-filenameproc-lambda"],
  ])

  # Ancillary Lambda
  ancillary_lambdas = flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-id-sync-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-delta-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}_get_status"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-redis-sync-lambda"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-mesh-processor-lambda" if var.environment != "dev"],
  ])

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

  sqs_queues = distinct(flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ack-metadata-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-batch-file-created-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-delta-dlq"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-metadata-queue.fifo"],
    var.environment == "dev" ? [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-id-sync-dlq"] : ["imms-${var.environment}-id-sync-dlq"],
    var.environment == "dev" ? [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-id-sync-queue"] : ["imms-${var.environment}-id-sync-queue"],
  ]))

  # ECS (cluster names match instance short_prefix: imms-<sub_env>-ecs-cluster)
  ecs_clusters = [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ecs-cluster"]

  redis_cache_cluster_id = "immunisation-redis-replication-group-001"

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
          "metrics" : concat(
            [for lambda in local.api_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { region : var.aws_region }]],
            [for lambda in local.api_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region }]]
          ),
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
          "metrics" : concat(
            [[{ expression : "AVG(METRICS())", label : "Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
            [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "m${i + 1}", region : var.aws_region }]]
          ),
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
          "metrics" : [
            for lambda in local.api_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { region : var.aws_region }]
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
        "y" : 10,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : concat(
            [[{ expression : "SUM(METRICS())", label : "API Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
            [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region, id : "m${i + 1}", visible : false }]]
          ),
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
          "metrics" : concat(
            [for lambda in local.batch_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { region : var.aws_region }]],
            [for lambda in local.batch_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region }]]
          ),
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
          "metrics" : concat(
            [[{ expression : "AVG(METRICS())", label : "Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
            [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "m${i + 1}", region : var.aws_region }]]
          ),
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
          "metrics" : [
            for lambda in local.batch_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { region : var.aws_region }]
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
        "y" : 17,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : concat(
            [[{ expression : "SUM(METRICS())", label : "API Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
            [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region, id : "m${i + 1}", visible : false }]]
          ),
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
          "metrics" : concat(
            [for lambda in local.ancillary_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { region : var.aws_region }]],
            [for lambda in local.ancillary_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region }]]
          ),
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
          "metrics" : concat(
            [[{ expression : "AVG(METRICS())", label : "Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
            [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "m${i + 1}", region : var.aws_region }]]
          ),
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
          "metrics" : [
            for lambda in local.ancillary_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { region : var.aws_region }]
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
        "y" : 24,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : concat(
            [[{ expression : "SUM(METRICS())", label : "API Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
            [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { color : local.errors_colour_code, region : var.aws_region, id : "m${i + 1}", visible : false }]]
          ),
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
          "metrics" : concat(
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "GetItem", { region : var.aws_region }]],
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "Query", { region : var.aws_region }]]
          ),
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
          "metrics" : concat(
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "GetItem", { region : var.aws_region }]],
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "Query", { region : var.aws_region }]]
          ),
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
          "metrics" : [
            for table in local.dynamodb_tables : ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table]
          ],
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
          "metrics" : concat(
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "PutItem", { region : var.aws_region }]],
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "UpdateItem", { region : var.aws_region }]]
          ),
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
          "metrics" : concat(
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "PutItem", { region : var.aws_region }]],
            [for table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "UpdateItem", { region : var.aws_region }]]
          ),
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
          "metrics" : [
            for table in local.dynamodb_tables : ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", table]
          ],
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
          "markdown" : "## ECS"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 44,
        "width" : 8,
        "height" : 6,
        "properties" : {
          "metrics" : [
            for cluster in local.ecs_clusters : ["ECS/ContainerInsights", "TaskCount", "ClusterName", cluster, { region : var.aws_region }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "SampleCount",
          "period" : 300,
          "title" : "ECS - Task Count"
        }
      },
      {
        "type" : "metric",
        "x" : 8,
        "y" : 44,
        "width" : 8,
        "height" : 6,
        "properties" : {
          "metrics" : [
            for cluster in local.ecs_clusters : ["ECS/ContainerInsights", "CpuUtilized", "ClusterName", cluster, { region : var.aws_region }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ECS - CPU Utilization"
        }
      },
      {
        "type" : "metric",
        "x" : 16,
        "y" : 44,
        "width" : 8,
        "height" : 6,
        "properties" : {
          "metrics" : [
            for cluster in local.ecs_clusters : ["ECS/ContainerInsights", "MemoryUtilized", "ClusterName", cluster, { region : var.aws_region }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ECS - Memory Utilization"
        }
      },
      {
        "type" : "text",
        "x" : 0,
        "y" : 50,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "## Other"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 51,
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
        "y" : 51,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : [
            for sub_env in local.sub_environments_map[var.environment] : ["AWS/Kinesis", "IncomingBytes", "StreamName", "imms-${sub_env}-processingdata-stream"]
          ],
          "region" : var.aws_region,
          "title" : "Kinesis - IncomingBytes"
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 51,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", queue, { region : var.aws_region }]
          ],
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
        "y" : 57,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : [
            ["AWS/ElastiCache", "CacheHits", "CacheClusterId", local.redis_cache_cluster_id, "CacheNodeId", "0001"]
          ],
          "region" : var.aws_region,
          "title" : "ElastiCache - CacheHits",
          "period" : 300,
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 57,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", local.redis_cache_cluster_id, "CacheNodeId", "0001"]
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
        "y" : 63,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "# Alarms"
        }
      },
      {
        "type" : "alarm",
        "x" : 0,
        "y" : 64,
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
