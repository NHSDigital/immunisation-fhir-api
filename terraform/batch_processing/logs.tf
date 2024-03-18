resource "aws_cloudwatch_log_group" "batch_task_log_group" {
  name              = "${local.prefix}-task"
  retention_in_days = 30
}
