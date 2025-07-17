locals {
  zone_subdomain = var.project_short_name
}

data "aws_route53_zone" "project_zone" {
  name = "imms.int.vds.platform.nhs.uk"
}
