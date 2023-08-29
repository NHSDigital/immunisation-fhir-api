module "api_gateway" {
  source = "./api_gateway"

  prefix          = local.prefix
  short_prefix    = local.short_prefix
  zone_id         = aws_route53_zone.project_zone.zone_id
  api_domain_name = local.service_domain_name
  environment     = local.environment
}
