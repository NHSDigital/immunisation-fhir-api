resource "aws_cloudwatch_dashboard" "imms-metrics-dashboard" {
  dashboard_name = "imms-metrics-dashboard-${var.environment}"
  dashboard_body = file("${path.root}/dashboards/imms-metrics-dashboard-${var.environment}.json")
}

