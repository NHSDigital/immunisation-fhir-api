resource "aws_iam_role" "eventbridge_forwarder_role" {
  name = "imms-${var.environment}-eventbridge-forwarder-role"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement = [{
      Sid      = "TrustEventBridgeService",
      Effect   = "Allow",
      Principal = { Service = "events.amazonaws.com" },
      Action   = "sts:AssumeRole",
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = var.imms_account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_forwarder_policy" {
  name = "imms-${var.environment}-eventbridge-forwarder-policy"
  role = aws_iam_role.eventbridge_forwarder_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid    = "ActionsForResource",
      Effect = "Allow",
      Action = ["events:PutEvents"],
      Resource = [
        "arn:aws:events:eu-west-2:${var.csoc_account_id}:event-bus/shield-eventbus"
      ]
    }]
  })
}
