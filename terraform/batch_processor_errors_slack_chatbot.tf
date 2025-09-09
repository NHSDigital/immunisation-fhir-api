resource "awscc_chatbot_slack_channel_configuration" "batch_processor_errors" {
  count              = var.batch_error_notifications_enabled ? 1 : 0

  configuration_name = "${local.resource_scope}-batch-processor-errors-slack-channel-config"
  iam_role_arn       = awscc_iam_role.batch_processor_errors_chatbot[0].arn
  slack_channel_id   = var.environment == "prod" ? "TODO - make channel" : "C09E48NDP18"
  slack_workspace_id = "TJ00QR03U"
  sns_topic_arns     = [aws_sns_topic.batch_processor_errors[0].arn]
}

resource "awscc_iam_role" "batch_processor_errors_chatbot" {
  count = var.batch_error_notifications_enabled ? 1 : 0

  role_name = "${local.resource_scope}-batch-processor-errors-chatbot-channel-role"
  assume_role_policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "chatbot.amazonaws.com"
        }
      },
    ]
  })
  managed_policy_arns = ["arn:aws:iam::aws:policy/AWSResourceExplorerReadOnlyAccess"]
}
