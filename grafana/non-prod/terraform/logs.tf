############################################################################################################
#logs.tf
# logs.tf

# Set up CloudWatch group and log stream and retain logs for 30 days
resource "aws_cloudwatch_log_group" "grafana_log_group" {
  name = local.log_group
  retention_in_days = 30

  tags = merge(var.tags, {
      Name = local.log_group
  })
}

resource "aws_cloudwatch_log_stream" "grafana_log_group" {
  name = "${local.log_group}-stream"
  log_group_name = aws_cloudwatch_log_group.grafana_log_group.name
}
