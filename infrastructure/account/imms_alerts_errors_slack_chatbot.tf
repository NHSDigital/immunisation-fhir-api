resource "aws_chatbot_slack_channel_configuration" "imms_system_alert_errors" {
  configuration_name = "${var.environment}-imms-system-alert-errors-slack-channel-config"
  iam_role_arn       = aws_iam_role.imms_system_alert_errors_chatbot.arn
  slack_channel_id   = var.environment == "prod" ? "C09EA0HE202" : "C09E48NDP18"
  slack_team_id      = "TJ00QR03U"
  sns_topic_arns     = [aws_sns_topic.imms_system_alert_errors.arn]
}

resource "aws_iam_role" "imms_system_alert_errors_chatbot" {
  name = "${var.environment}-imms-system-alert-errors-chatbot-channel-role"
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
