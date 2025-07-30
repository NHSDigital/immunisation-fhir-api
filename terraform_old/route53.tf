locals {
  zone_subdomain = var.project_short_name
}

data "aws_route53_zone" "project_zone" {
  name = "imms.${var.aws_account_name}.vds.platform.nhs.uk"
}
