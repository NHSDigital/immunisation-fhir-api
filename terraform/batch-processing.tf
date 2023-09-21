module "batch-processing" {
    source = "./batch-processing"
    environment = local.environment
    prefix = local.prefix
    short_prefix = local.short_prefix
}
