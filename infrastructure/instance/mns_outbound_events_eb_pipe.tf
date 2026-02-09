# IAM Role for EventBridge Pipe
resource "aws_iam_role" "mns_outbound_events_eb_pipe" {
  name = "${local.resource_scope}-mns-outbound-eventbridge-pipe-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "pipes.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = var.immunisation_account_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "mns_outbound_events_eb_pipe_source_policy" {
  role = aws_iam_role.mns_outbound_events_eb_pipe.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ],
        "Resource" : aws_dynamodb_table.events-dynamodb-table.stream_arn
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ],
        "Resource" : data.aws_kms_key.existing_dynamo_encryption_key.arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "mns_outbound_events_eb_pipe_target_policy" {
  role = aws_iam_role.mns_outbound_events_eb_pipe.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:GetQueueAttributes",
          "sqs:SendMessage",
        ],
        Resource = [
          aws_sqs_queue.mns_outbound_events.arn,
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy" "mns_outbound_events_eb_pipe_cw_log_policy" {
  role = aws_iam_role.mns_outbound_events_eb_pipe.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/vendedlogs/pipes/${local.resource_scope}-mns-outbound-event-pipe-logs:*",
        ]
      },
    ]
  })
}

resource "aws_cloudwatch_log_group" "mns_outbound_events_eb_pipe" {
  name              = "/aws/vendedlogs/pipes/${local.resource_scope}-mns-outbound-event-pipe-logs"
  retention_in_days = 30
}

resource "aws_pipes_pipe" "mns_outbound_events" {
  depends_on = [
    aws_iam_role_policy.mns_outbound_events_eb_pipe_source_policy,
    aws_iam_role_policy.mns_outbound_events_eb_pipe_target_policy,
    aws_iam_role_policy.mns_outbound_events_eb_pipe_cw_log_policy,
  ]
  name     = "${local.resource_scope}-mns-outbound-events"
  role_arn = aws_iam_role.mns_outbound_events_eb_pipe.arn
  source   = aws_dynamodb_table.events-dynamodb-table.stream_arn
  target   = aws_sqs_queue.mns_outbound_events.arn

  source_parameters {
    dynamodb_stream_parameters {
      starting_position = "TRIM_HORIZON"
    }
  }

  log_configuration {
    include_execution_data = ["ALL"]
    level                  = "ERROR"
    cloudwatch_logs_log_destination {
      log_group_arn = aws_cloudwatch_log_group.pipe_log_group.arn
    }
  }
}

# TODO - look into adding filter for DPS events
# TODO - include error logs
