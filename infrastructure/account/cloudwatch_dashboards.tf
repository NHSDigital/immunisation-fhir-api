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
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-mns-publisher-lambda"],
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
    var.environment == "dev" ? "immunisation-batch-internal-qa-audit-table" : "",
  ])

  mns_resource_scopes = var.environment == "dev" ? local.sub_environments_map[var.environment] : [var.environment]
  mns_sqs_queues = flatten([
    [for resource_scope in local.mns_resource_scopes : "${resource_scope}-mns-outbound-events-queue"],
    [for resource_scope in local.mns_resource_scopes : "${resource_scope}-mns-outbound-events-dead-letter-queue"],
    var.environment == "dev" ? [for resource_scope in local.mns_resource_scopes : "${resource_scope}-mns-test-notification-queue"] : [],
  ])

  sqs_queues = distinct(flatten([
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ack-metadata-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-batch-file-created-queue.fifo"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-delta-dlq"],
    [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-metadata-queue.fifo"],
    var.environment == "dev" ? [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-id-sync-dlq"] : ["imms-${var.environment}-id-sync-dlq"],
    var.environment == "dev" ? [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-id-sync-queue"] : ["imms-${var.environment}-id-sync-queue"],
    local.mns_sqs_queues,
  ]))

  # ECS (cluster names match instance short_prefix: imms-<sub_env>-ecs-cluster)
  ecs_clusters                 = [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-ecs-cluster"]
  ecs_task_definition_families = [for sub_env in local.sub_environments_map[var.environment] : "imms-${sub_env}-processor-task"]

  # Alarms
  alarms = concat([
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
    "-ack-lambda-error",
    "-forwarding-lambda-error",
    "-id-sync-lambda-error",
    "-redis-sync-lambda-error",
    "-delta-lambda-error",
    "-mns-publisher-lambda-error",
    "_not_found-lambda-error",
    "_not_found memory alarm"
  ], var.environment == "dev" ? [] : ["-mesh-processor-lambda-error"])
  # Alarms are turned off in internal-qa as testing could cause unnecessary noise
  dev_alarms = [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-internal-dev${alarm}"]
  non_dev_alarms = flatten([for sub_env in local.sub_environments_map[var.environment] :
  [for alarm in local.alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${sub_env}${alarm}"] if var.environment != "dev"])
  shared_alarms = var.environment == "dev" ? [] : [
    "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${var.environment}-mesh-processor-no-lambda-invocation"
  ]
  alarms_properties = var.environment == "dev" ? local.dev_alarms : concat(local.non_dev_alarms, local.shared_alarms)

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
            [
              [{ expression : "SUM(METRICS(\"apiinvocations\"))", label : "API Invocations", id : "e1", region : var.aws_region }],
              [{ expression : "SUM(METRICS(\"apierrors\"))", label : "API Errors", id : "e2", color : local.errors_colour_code, region : var.aws_region }]
            ],
            [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { id : "apiinvocations${i}", visible : false, region : var.aws_region }]],
            [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { id : "apierrors${i}", visible : false, color : local.errors_colour_code, region : var.aws_region }]]
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
            [[{ expression : "AVG(METRICS(\"apiduration\"))", label : "API Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
            [for i, lambda in local.api_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "apiduration${i}", visible : false, region : var.aws_region }]]
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
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"apiconcurrency\"))", label : "API ConcurrentExecutions", id : "e1", region : var.aws_region }]],
            [for i, lambda in local.api_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { id : "apiconcurrency${i}", visible : false, region : var.aws_region }]]
          ),
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
            [
              [{ expression : "SUM(METRICS(\"batchinvocations\"))", label : "Batch Invocations", id : "e1", region : var.aws_region }],
              [{ expression : "SUM(METRICS(\"batcherrors\"))", label : "Batch Errors", id : "e2", color : local.errors_colour_code, region : var.aws_region }]
            ],
            [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { id : "batchinvocations${i}", visible : false, region : var.aws_region }]],
            [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { id : "batcherrors${i}", visible : false, color : local.errors_colour_code, region : var.aws_region }]]
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
            [[{ expression : "AVG(METRICS(\"batchduration\"))", label : "Batch Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
            [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "batchduration${i}", visible : false, region : var.aws_region }]]
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
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"batchconcurrency\"))", label : "Batch ConcurrentExecutions", id : "e1", region : var.aws_region }]],
            [for i, lambda in local.batch_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { id : "batchconcurrency${i}", visible : false, region : var.aws_region }]]
          ),
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
            [[{ expression : "SUM(METRICS())", label : "Batch Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
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
            [
              [{ expression : "SUM(METRICS(\"ancillaryinvocations\"))", label : "Ancillary Invocations", id : "e1", region : var.aws_region }],
              [{ expression : "SUM(METRICS(\"ancillaryerrors\"))", label : "Ancillary Errors", id : "e2", color : local.errors_colour_code, region : var.aws_region }]
            ],
            [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Invocations", "FunctionName", lambda, { id : "ancillaryinvocations${i}", visible : false, region : var.aws_region }]],
            [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Errors", "FunctionName", lambda, { id : "ancillaryerrors${i}", visible : false, color : local.errors_colour_code, region : var.aws_region }]]
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
            [[{ expression : "AVG(METRICS(\"ancillaryduration\"))", label : "Ancillary Average Duration", id : "e1", stat : "Maximum", region : var.aws_region }]],
            [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "Duration", "FunctionName", lambda, { stat : "Maximum", id : "ancillaryduration${i}", visible : false, region : var.aws_region }]]
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
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"ancillaryconcurrency\"))", label : "Ancillary ConcurrentExecutions", id : "e1", region : var.aws_region }]],
            [for i, lambda in local.ancillary_lambdas : ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", lambda, { id : "ancillaryconcurrency${i}", visible : false, region : var.aws_region }]]
          ),
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
            [[{ expression : "SUM(METRICS())", label : "Ancillary Errors", id : "e1", region : var.aws_region, color : local.errors_colour_code }]],
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
            [[{ expression : "SUM(METRICS(\"ddbreadcount\"))", label : "Successful Read Requests", id : "e1", region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "GetItem", { id : "ddbreadcountget${i}", visible : false, region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "Query", { id : "ddbreadcountquery${i}", visible : false, region : var.aws_region }]]
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
            [[{ expression : "AVG(METRICS(\"ddbreadlatency\"))", label : "Average Read Latency", id : "e1", region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "GetItem", { id : "ddbreadlatencyget${i}", visible : false, region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "Query", { id : "ddbreadlatencyquery${i}", visible : false, region : var.aws_region }]]
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
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"ddbreadcapacity\"))", label : "Consumed Read Capacity Units", id : "e1", region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table, { id : "ddbreadcapacity${i}", visible : false, region : var.aws_region }]]
          ),
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
            [[{ expression : "SUM(METRICS(\"ddbwritecount\"))", label : "Successful Write Requests", id : "e1", region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "PutItem", { id : "ddbwritecountput${i}", visible : false, region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "UpdateItem", { id : "ddbwritecountupdate${i}", visible : false, region : var.aws_region }]]
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
            [[{ expression : "AVG(METRICS(\"ddbwritelatency\"))", label : "Average Write Latency", id : "e1", region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "PutItem", { id : "ddbwritelatencyput${i}", visible : false, region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", table, "Operation", "UpdateItem", { id : "ddbwritelatencyupdate${i}", visible : false, region : var.aws_region }]]
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
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"ddbwritecapacity\"))", label : "Consumed Write Capacity Units", id : "e1", region : var.aws_region }]],
            [for i, table in local.dynamodb_tables : ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", table, { id : "ddbwritecapacity${i}", visible : false, region : var.aws_region }]]
          ),
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
            for i, cluster in local.ecs_clusters : ["ECS/ContainerInsights", "TaskCount", "ClusterName", cluster, "TaskDefinitionFamily", local.ecs_task_definition_families[i], { region : var.aws_region }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Average",
          "period" : 300,
          "title" : "ECS Batch Processor - Task Count"
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
            for i, cluster in local.ecs_clusters : ["ECS/ContainerInsights", "CpuUtilized", "ClusterName", cluster, "TaskDefinitionFamily", local.ecs_task_definition_families[i], { region : var.aws_region }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ECS Batch Processor - CPU Utilization"
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
            for i, cluster in local.ecs_clusters : ["ECS/ContainerInsights", "MemoryUtilized", "ClusterName", cluster, "TaskDefinitionFamily", local.ecs_task_definition_families[i], { region : var.aws_region }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Maximum",
          "period" : 300,
          "title" : "ECS Batch Processor - Memory Utilization"
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
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"sqssent\"))", label : "Messages Sent", id : "e1", region : var.aws_region }]],
            [for i, queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", queue, { id : "sqssent${i}", visible : false, region : var.aws_region }]]
          ),
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
        "x" : 18,
        "y" : 51,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : concat(
            [[{ expression : "SUM(METRICS(\"sqsvisible\"))", label : "Visible Messages", id : "e1", region : var.aws_region }]],
            [for i, queue in local.sqs_queues : ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", queue, { id : "sqsvisible${i}", visible : false, region : var.aws_region }]]
          ),
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "SQS Queues - Visible Messages",
          "period" : 300,
          "stat" : "Maximum"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 57,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : concat(
            [[{ expression : "MAX(METRICS(\"sqsoldest\"))", label : "Oldest Message Age", id : "e1", region : var.aws_region }]],
            [for i, queue in local.sqs_queues : ["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", queue, { id : "sqsoldest${i}", visible : false, region : var.aws_region }]]
          ),
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "title" : "SQS Queues - Oldest Message Age",
          "period" : 300,
          "stat" : "Maximum"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 57,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "view" : "timeSeries",
          "stacked" : false,
          "metrics" : [
            ["AWS/ElastiCache", "CacheHits", "CacheClusterId", "immunisation-redis-cluster", "CacheNodeId", "0001"]
          ],
          "region" : var.aws_region,
          "title" : "ElastiCache - CacheHits",
          "period" : 300,
        }
      },
      {
        "type" : "metric",
        "x" : 12,
        "y" : 57,
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
