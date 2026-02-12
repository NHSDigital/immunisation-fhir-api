resource "aws_cloudwatch_dashboard" "imms-metrics-dashboard-dev" {
  count          = var.environment == "dev" && !local.is_temp ? 1 : 0
  dashboard_name = "imms-metrics-dashboard-dev"
  dashboard_body = file("${path.root}/imms-metrics-dashboard-dev.json")
}
