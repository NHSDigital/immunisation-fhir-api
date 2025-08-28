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

# TODO un-hardcode the region
# e.g.
#   "logs.${data.aws_region.current.region}.amazonaws.com"

resource "aws_iam_role" "api_logs_subscription_role" {
  name = "${var.short_prefix}-api-logs-subscription-role"
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

resource "aws_cloudwatch_log_subscription_filter" "api_logs_subscription_logfilter" {
  name            = "${var.short_prefix}-api-logs-subscription-logfilter"
  log_group_name  = aws_cloudwatch_log_group.api_access_log.name
  filter_pattern  = ""
  destination_arn = "arn:aws:logs:eu-west-2:693466633220:destination:api_gateway_log_destination"
  role_arn        = aws_iam_role.api_logs_subscription_role.arn
}
