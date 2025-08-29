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