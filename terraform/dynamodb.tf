module "dynamodb" {
  source = "./dynamodb"
  prefix          = local.prefix
  short_prefix    = local.short_prefix
  environment     = local.environment
}
