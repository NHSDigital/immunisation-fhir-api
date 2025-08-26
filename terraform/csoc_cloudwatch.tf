resource "aws_iam_role" "eventbridge_forwarder_role" {
  name = "${local.short_prefix}-eventbridge-forwarder-role"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement = [{
      Sid      = "TrustEventBridgeService",
      Effect   = "Allow",
      Principal = { Service = "events.amazonaws.com" },
      Action   = "sts:AssumeRole",
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = var.immunisation_account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_forwarder_policy" {
  name = "${local.short_prefix}-eventbridge-forwarder-policy"
  role = aws_iam_role.eventbridge_forwarder_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid    = "ActionsForResource",
      Effect = "Allow",
      Action = ["events:PutEvents"],
      Resource = [
        "arn:aws:events:eu-west-2:693466633220:event-bus/shield-eventbus"
      ]
    }]
  })
}



























resource "aws_iam_role" "dynamo_s3_access_role" {
  name = "${local.short_prefix}-dynamo-s3-access-role"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${var.dspp_core_account_id}:root"
        },
        Action : "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "dynamo_s3_access_policy" {
  name = "${local.short_prefix}-dynamo_s3_access-policy"
  role = aws_iam_role.dynamo_s3_access_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ],
        Resource = [
          aws_dynamodb_table.delta-dynamodb-table.arn,
          "${aws_dynamodb_table.delta-dynamodb-table.arn}/index/*"
        ]
      }
    ]
  })
}
