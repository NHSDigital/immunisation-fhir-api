resource "aws_chatbot_slack_channel_configuration" "batch_processor_errors" {
  configuration_name = "${var.environment}-batch-processor-errors-slack-channel-config"
  iam_role_arn       = aws_iam_role.batch_processor_errors_chatbot.arn
  slack_channel_id   = var.environment == "prod" ? "C09EA0HE202" : "C09E48NDP18"
  slack_team_id      = "TJ00QR03U"
  sns_topic_arns     = [aws_sns_topic.batch_processor_errors.arn]
}

resource "aws_iam_role" "batch_processor_errors_chatbot" {
  name               = "${var.environment}-batch-processor-errors-chatbot-channel-role"
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
  # To try: could test without this?
  managed_policy_arns = ["arn:aws:iam::aws:policy/AWSResourceExplorerReadOnlyAccess"]
}
