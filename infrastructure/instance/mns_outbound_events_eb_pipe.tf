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
            "aws:SourceAccount" = "${var.immunisation_account_id}"
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
        Effect = "Allow",
        Action = [
          "iam:PassRole"
        ],
        Resource = aws_iam_role.mns_outbound_events_eb_pipe.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "mns_outbound_events_eb_pipe_target_policy" {
  role = aws_iam_role.example.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
        ],
        Resource = [
          aws_sqs_queue.mns_outbound_events.arn,
        ]
      },
    ]
  })
}

resource "aws_pipes_pipe" "mns_outbound_events" {
  depends_on = [
    aws_iam_role_policy.mns_outbound_events_eb_pipe_source_policy,
    aws_iam_role_policy.mns_outbound_events_eb_pipe_target_policy
  ]
  name     = "${local.resource_scope}-mns-outbound-events"
  role_arn = aws_iam_role.mns_outbound_events.arn
  source   = aws_dynamodb_table.events-dynamodb-table.stream_arn
  target   = aws_sqs_queue.mns_outbound_events.arn
}

# TODO - look into adding filter for DPS events
