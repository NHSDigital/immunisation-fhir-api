module "catch_all_lambda" {
  source = "./catch_all_lambda"
  prefix          = local.prefix
  short_prefix    = local.short_prefix
  environment     = local.environment
}