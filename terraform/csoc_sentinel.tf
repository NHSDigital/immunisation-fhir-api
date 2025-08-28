# https://nhsd-confluence.digital.nhs.uk/spaces/CCEP/pages/407374909/API+Gateway+Access+Logs

# 2. IAM Role for Cross Account Log Subscriptions
resource "aws_iam_role" "cwlogs_subscription_role" {
  name = "${local.short_prefix}-cwlogs-subscription-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid    = "",
      Principal = {
        Service = "logs.eu-west-2.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# 3. Log Group
resource "aws_cloudwatch_log_group" "cwlogs_subscription_log_group" {
  name              = "/aws/cloudwatch/${local.short_prefix}-cwlogs-subscription-log-group"
  retention_in_days = 30
}

# Permissions Policy for Subscription Filter
# TODO: un-hardcode the destination account ID
resource "aws_iam_policy" "cwlogs_subscription_policy" {
  name = "${local.short_prefix}-cwlogs-subscription-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid = "AllowPutAPIGSubFilter"
        Effect = "Allow"
        Action = [
          "logs:PutSubscriptionFilter"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/cloudwatch/${local.short_prefix}-cwlogs-subscription-log-group:*",
          "arn:aws:logs:eu-west-2:693466633220:destination:api_gateway_log_destination"
        ]
      }
    ]
  })
}

# 4. Subscription Filter
resource "aws_cloudwatch_log_subscription_filter" "cwlogs_subscription_logfilter" {
  name            = "${local.short_prefix}-cwlogs-subscription-logfilter"
  log_group_name  = aws_cloudwatch_log_group.cwlogs_subscription_log_group.name
  filter_pattern  = ""
  destination_arn = "arn:aws:logs:eu-west-2:693466633220:destination:api_gateway_log_destination"
  role_arn        = aws_iam_role.cwlogs_subscription_role.arn
}

# 5. API Gateway Log Role
resource "aws_iam_role" "cwlogs_apigateway_log_role" {
  name = "${local.short_prefix}-cwlogs-apigateway-log-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid    = "",
      Principal = {
        Service = "apigateway.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cwlogs_apigateway_policy" {
  role       = aws_iam_role.cwlogs_apigateway_log_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# 6. Log Forwarding from API Gateway
# TODO
