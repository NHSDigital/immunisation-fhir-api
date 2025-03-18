############################################################################################################
#logs.tf
# logs.tf

# Set up CloudWatch group and log stream and retain logs for 30 days
resource "aws_cloudwatch_log_group" "grafana_log_group" {
  name              = var.log_group
  retention_in_days = 30

  tags = merge(var.tags, {
      Name = "${var.prefix}-log-group"
  })
}

resource "aws_cloudwatch_log_stream" "grafana_log_group" {
  name           = "${var.prefix}-log-stream"
  log_group_name = aws_cloudwatch_log_group.grafana_log_group.name
}
