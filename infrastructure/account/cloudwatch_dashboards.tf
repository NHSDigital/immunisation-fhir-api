locals {
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
  non_dev_blue      = var.environment == "prod" ? "blue" : "int-blue"
  non_dev_green     = var.environment == "prod" ? "green" : "int-green"
  dev_alarms        = [for alarm in alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-internal-dev${alarm}"]
  blue_alarms       = [for alarm in alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${local.non_dev_blue}${alarm}"]
  green_alarms      = [for alarm in alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${local.non_dev_green}${alarm}"]
  non_dev_alarms    = concat(local.blue_alarms, local.green_alarms)
  alarms_properties = var.environment == "dev" ? local.dev_alarms : local.non_dev_alarms

  # DynamoDB
  dynamodb_tables = compact([
    "imms-${var.environment == "dev" ? "internal-dev" : var.environment}-delta",
    var.environment == "dev" ? "imms-internal-qa-delta" : "",
    "imms-${var.environment == "dev" ? "internal-dev" : var.environment}-imms-events",
    var.environment == "dev" ? "imms-internal-qa--imms-events" : "",
    "immunisation-batch-${var.environment == "dev" ? "internal-dev" : var.environment}-audit-table",
    var.environment == "dev" ? "imms-internal-qa--audit-table" : "",
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
  green_sqs_queue_metrics        = [for queue in local.sqs_queues : ["AWS/SQS", "NumberOfMessagesSent", "QueueName", queue == "id-sync-dlq" || queue == "id-sync-queue" ? "imms-${var.environment}-${queue}" : "imms-${local.non_dev_green}-${queue}", { region : var.aws_region }]]
  non_dev_sqs_queue_metrics      = concat(local.blue_sqs_queue_metrics, local.green_sqs_queue_metrics)
  sqs_queue_metrics              = var.environment == "dev" ? local.dev_sqs_queue_metrics : local.non_dev_sqs_queue_metrics
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
        "type" : "metric",
        "x" : 0,
        "y" : 2,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/Lambda", "Invocations", { region : var.aws_region }],
            [".", "Errors", { color : "#d62728", region : var.aws_region }],
            [
              ".",
              "ConcurrentExecutions",
              { region : var.aws_region, visible : false }
            ]
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
        "x" : 18,
        "y" : 2,
        "width" : 2,
        "height" : 3,
        "properties" : {
          "metrics" : [
            [
              "AWS/Lambda",
              "Errors",
              { region : var.aws_region, color : "#d62728" }
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
        "type" : "metric",
        "x" : 6,
        "y" : 2,
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
        "type" : "text",
        "x" : 0,
        "y" : 21,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "## Other"
        }
      },
      {
        "type" : "alarm",
        "x" : 0,
        "y" : 29,
        "width" : 24,
        "height" : var.environment == dev ? 4 : 8,
        "properties" : {
          "alarms" : local.alarms_properties
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
        "type" : "metric",
        "x" : 12,
        "y" : 2,
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
          "title" : "Max ConcurrentExecutions"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 9,
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
        "x" : 18,
        "y" : 9,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/DynamoDB",
              "UserErrors",
              "Operation",
              "GetRecords",
              { color : "#d62728", region : var.aws_region }
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
        "x" : 6,
        "y" : 9,
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
        "type" : "text",
        "x" : 0,
        "y" : 8,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "## DynamoDB"
        }
      },
      {
        "type" : "metric",
        "x" : 0,
        "y" : 22,
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
        "type" : "text",
        "x" : 0,
        "y" : 28,
        "width" : 24,
        "height" : 1,
        "properties" : {
          "markdown" : "# Alarms"
        }
      },
      {
        "type" : "metric",
        "x" : 6,
        "y" : 22,
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
        "y" : 22,
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
        "x" : 12,
        "y" : 9,
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
        "x" : 12,
        "y" : 15,
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
        "type" : "metric",
        "x" : 0,
        "y" : 15,
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
        "y" : 15,
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
        "x" : 18,
        "y" : 22,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            ["AWS/ElastiCache", "CacheHits", { region : var.aws_region, color : "#ff7f0e" }]
          ],
          "view" : "timeSeries",
          "stacked" : false,
          "region" : var.aws_region,
          "stat" : "Sum",
          "period" : 300,
          "title" : "ElastiCache - CacheHits"
        }
      }
    ]
    }
  )
}
