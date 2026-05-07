resource "aws_chatbot_slack_channel_configuration" "fhir_api_perf_alerts" {
  configuration_name = "${var.environment}-fhir-api-perf-alerts-slack-channel-config"
  iam_role_arn       = aws_iam_role.fhir_api_perf_alerts_chatbot.arn
  slack_channel_id   = var.environment == "prod" ? "C0B11MJPQ6A" : "C0B1GKZ5S4R"
  slack_team_id      = "TJ00QR03U"
  sns_topic_arns     = [aws_sns_topic.fhir_api_perf_alerts.arn]
}

resource "aws_iam_role" "fhir_api_perf_alerts_chatbot" {
  name = "${var.environment}-fhir-api-perf-alerts-chatbot-channel-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = "AssumeChatbotRole"
        Principal = {
          Service = "chatbot.amazonaws.com"
        }
      },
    ]
  })
}
