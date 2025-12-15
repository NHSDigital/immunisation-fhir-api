resource "aws_chatbot_slack_channel_configuration" "fhir_api_errors" {
  configuration_name = "${var.environment}-fhir-api-errors-slack-channel-config"
  iam_role_arn       = aws_iam_role.fhir_api_errors_chatbot.arn
  slack_channel_id   = var.environment == "prod" ? "C0A3LPKNKEE" : "C0A4F3G8J0G"
  slack_team_id      = "TJ00QR03U"
  sns_topic_arns     = [aws_sns_topic.fhir_api_errors.arn]
}

resource "aws_iam_role" "fhir_api_errors_chatbot" {
  name = "${var.environment}-fhir-api-errors-chatbot-channel-role"
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
