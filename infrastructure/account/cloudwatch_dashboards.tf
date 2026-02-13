locals {
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
  dev_alarms     = [for alarm in alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-internal-dev${alarm}"]
  blue_alarms    = [for alarm in alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${var.environment == "prod" ? "blue" : "int-blue"}${alarm}"]
  green_alarms   = [for alarm in alarms : "arn:aws:cloudwatch:${var.aws_region}:${var.imms_account_id}:alarm:imms-${var.environment == "prod" ? "green" : "int-green"}${alarm}"]
  non_dev_alarms = concat(local.blue_alarms, local.green_alarms)

  sub_envs_a = var.environment == dev ? "internal-dev" : var.environment == "prod" ? "blue" : "int-blue"
  sub_envs_b = var.environment == dev ? "internal-qa" : var.environment == "prod" ? "green" : "int-green"
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
          "alarms" : var.environment == dev ? local.dev_alarms : local.non_dev_alarms
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
          "metrics" : [
            ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "imms-internal-dev-delta", "Operation", "GetItem", { region : var.aws_region }],
            ["...", "imms-internal-qa-delta", ".", ".", { region : var.aws_region }],

            ["...", "imms-internal-dev-delta", ".", "Query", { region : var.aws_region }],
            ["...", "imms-internal-qa-delta", ".", ".", { region : var.aws_region }],

            ["...", "imms-internal-dev-imms-events", ".", "GetItem", { region : var.aws_region }],
            ["...", "imms-internal-qa-imms-events", ".", ".", { region : var.aws_region }],

            ["...", "imms-internal-dev-imms-events", ".", "Query", { region : var.aws_region }],
            ["...", "imms-internal-qa-imms-events", ".", ".", { region : var.aws_region }],

            ["...", "immunisation-batch-internal-dev-audit-table", ".", "GetItem", { region : var.aws_region }],
            ["...", "immunisation-batch-internal-qa-audit-table", ".", ".", { region : var.aws_region }],

            ["...", "immunisation-batch-internal-dev-audit-table", ".", "Query", { region : var.aws_region }],
            ["...", "immunisation-batch-internal-qa-audit-table", ".", ".", { region : var.aws_region }],
          ],
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
          "metrics" : [
            [
              "AWS/DynamoDB",
              "SuccessfulRequestLatency",
              "TableName",
              "imms-internal-dev-delta",
              "Operation",
              "GetItem"
            ],
            ["...", "imms-internal-dev-imms-events", ".", "."],
            ["...", "immunisation-batch-internal-dev-audit-table", ".", "."],
            ["...", "imms-internal-dev-delta", ".", "Query"],
            ["...", "imms-internal-qa-imms-events", ".", "."],
            ["...", "GetItem"],
            ["...", "imms-internal-qa-delta", ".", "Query"],
            ["...", "immunisation-batch-internal-qa-audit-table", ".", "."],
            ["...", "GetItem"],
            ["...", "imms-internal-dev-imms-events", ".", "Query"],
            ["...", "immunisation-batch-internal-dev-audit-table", ".", "."]
          ],
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
          "metrics" : [
            [
              "AWS/Kinesis",
              "IncomingBytes",
              "StreamName",
              "imms-internal-dev-processingdata-stream"
            ],
            ["...", "imms-internal-qa-processingdata-stream"]
          ],
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
          "metrics" : [
            [
              "AWS/SQS",
              "NumberOfMessagesSent",
              "QueueName",
              "imms-internal-dev-batch-file-created-queue.fifo",
              { region : var.aws_region }
            ],
            ["...", "imms-internal-dev-id-sync-queue", { region : var.aws_region }],
            ["...", "imms-internal-qa-id-sync-dlq", { region : var.aws_region }],
            ["...", "imms-internal-qa-delta-dlq", { region : var.aws_region }],
            ["...", "imms-internal-dev-metadata-queue.fifo", { region : var.aws_region }],
            ["...", "imms-internal-qa-batch-file-created-queue.fifo", { region : var.aws_region }],
            ["...", "imms-internal-qa-id-sync-queue", { region : var.aws_region }],
            ["...", "imms-internal-dev-id-sync-dlq", { region : var.aws_region }],
            ["...", "imms-internal-dev-ack-metadata-queue.fifo", { region : var.aws_region }],
            ["...", "imms-internal-dev-delta-dlq", { region : var.aws_region }],
            ["...", "imms-internal-qa-ack-metadata-queue.fifo", { region : var.aws_region }],
            ["...", "imms-internal-qa-metadata-queue.fifo", { region : var.aws_region }]
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
        "x" : 12,
        "y" : 9,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/DynamoDB",
              "ConsumedReadCapacityUnits",
              "TableName",
              "imms-internal-qa-imms-events"
            ],
            ["...", "imms-internal-dev-delta"],
            ["...", "imms-internal-dev-imms-events"],
            ["...", "imms-internal-qa-delta"],
            ["...", "immunisation-batch-internal-qa-audit-table"],
            ["...", "immunisation-batch-internal-dev-audit-table"]
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
        "x" : 12,
        "y" : 15,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/DynamoDB",
              "ConsumedWriteCapacityUnits",
              "TableName",
              "immunisation-batch-internal-qa-audit-table"
            ],
            ["...", "imms-internal-dev-imms-events"],
            ["...", "imms-internal-qa-imms-events"],
            ["...", "imms-internal-dev-delta"],
            ["...", "immunisation-batch-internal-dev-audit-table"],
            ["...", "imms-internal-qa-delta"]
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
        "type" : "metric",
        "x" : 0,
        "y" : 15,
        "width" : 6,
        "height" : 6,
        "properties" : {
          "metrics" : [
            [
              "AWS/DynamoDB",
              "SuccessfulRequestLatency",
              "TableName",
              "imms-internal-qa-delta",
              "Operation",
              "GetItem",
              { region : var.aws_region }
            ],
            ["...", "imms-internal-dev-delta", ".", "PutItem", { region : var.aws_region }],
            ["...", "imms-internal-dev-imms-events", ".", "UpdateItem", { region : var.aws_region }],
            ["...", "PutItem", { region : var.aws_region }],
            ["...", "imms-internal-qa-delta", ".", ".", { region : var.aws_region }],
            ["...", "imms-internal-qa-imms-events", ".", "UpdateItem", { region : var.aws_region }],
            ["...", "PutItem", { region : var.aws_region }],
            ["...", "immunisation-batch-internal-dev-audit-table", ".", ".", { region : var.aws_region }],
            ["...", "UpdateItem", { region : var.aws_region }],
            ["...", "immunisation-batch-internal-qa-audit-table", ".", "PutItem", { region : var.aws_region }],
            ["...", "UpdateItem", { region : var.aws_region }]
          ],
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
          "metrics" : [
            [
              "AWS/DynamoDB",
              "SuccessfulRequestLatency",
              "TableName",
              "imms-internal-dev-delta",
              "Operation",
              "PutItem",
              { region : var.aws_region }
            ],
            ["...", "imms-internal-dev-imms-events", ".", "UpdateItem", { region : var.aws_region }],
            ["...", "imms-internal-qa-delta", ".", "PutItem", { region : var.aws_region }],
            ["...", "imms-internal-qa-imms-events", ".", ".", { region : var.aws_region }],
            ["...", "UpdateItem", { region : var.aws_region }]
          ],
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
