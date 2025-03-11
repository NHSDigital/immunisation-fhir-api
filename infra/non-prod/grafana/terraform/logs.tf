# logs.tf

# Set up CloudWatch group and log stream and retain logs for 30 days
resource "aws_cloudwatch_log_group" "grafana_log_group" {
  name              = "/ecs/grafana-app"
  retention_in_days = 30

  tags = {
    Name = "grafana-log-group"
  }
}

resource "aws_cloudwatch_log_stream" "grafana_log_group" {
  name           = "grafana-log-stream"
  log_group_name = aws_cloudwatch_log_group.grafana_log_group.name
}