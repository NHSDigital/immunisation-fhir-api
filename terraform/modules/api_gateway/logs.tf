resource "aws_cloudwatch_log_group" "api_access_log" {
  name              = "/aws/vendedlogs/${aws_apigatewayv2_api.service_api.id}/${var.sub_environment}"
  retention_in_days = 30
}

# TODO - This is global, so is overwritten by each deployment - move to infra Terraform?
resource "aws_api_gateway_account" "api_account" {
  cloudwatch_role_arn = aws_iam_role.api_cloudwatch.arn
}

resource "aws_iam_role" "api_cloudwatch" {
  name = "${var.short_prefix}-api-logs"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "cloudwatch" {
  name = "${var.prefix}-api-logs"
  role = aws_iam_role.api_cloudwatch.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:PutLogEvents",
                "logs:GetLogEvents",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "api_logs_apigateway_policy" {
  role       = aws_iam_role.api_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_iam_policy" "api_logs_subscription_policy" {
  name = "${var.short_prefix}-api-logs-subscription-policy"
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
          "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/vendedlogs/${aws_apigatewayv2_api.service_api.id}/${var.sub_environment}:*",
          "arn:aws:logs:${var.aws_region}:${var.csoc_account_id}:destination:api_gateway_log_destination"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_logs_subscription_policy" {
  role       = aws_iam_role.api_cloudwatch.name
  policy_arn = aws_iam_policy.api_logs_subscription_policy.arn
}

resource "aws_iam_role" "api_logs_subscription_role" {
  name = "${var.short_prefix}-api-logs-subscription-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid    = "",
      Principal = {
        Service = "logs.${var.aws_region}.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_subscription_filter" "api_logs_subscription_logfilter" {
  name            = "${var.short_prefix}-api-logs-subscription-logfilter"
  log_group_name  = aws_cloudwatch_log_group.api_access_log.name
  filter_pattern  = ""
  destination_arn = "arn:aws:logs:${var.aws_region}:${var.csoc_account_id}:destination:api_gateway_log_destination"
  role_arn        = aws_iam_role.api_logs_subscription_role.arn
}
