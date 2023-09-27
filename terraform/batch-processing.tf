module "batch-processing" {
    source = "./batch-processing"
    environment = local.environment
    prefix = local.prefix
    short_prefix = local.short_prefix
    service_domain_name = module.api_gateway.service_domain_name
}
