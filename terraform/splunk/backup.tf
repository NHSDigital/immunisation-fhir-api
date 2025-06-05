locals {
    environment         = terraform.workspace == "green" ? "prod" : terraform.workspace == "blue" ? "prod" : terraform.workspace
    // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.environment)) > 0
}
resource "aws_s3_bucket" "failed_logs_backup" {
    bucket = "${local.prefix}-failure-logs"
    // To facilitate deletion of non empty busckets
    force_destroy = local.is_temp
}
