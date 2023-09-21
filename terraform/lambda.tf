module "lambda" {
  source = "./lambda"
  prefix          = local.prefix
  short_prefix    = local.short_prefix
  environment     = local.environment
  dynamodb_table_name = module.dynamodb.dynamodb_table_name
}
