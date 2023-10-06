module "catch_all_lambda" {
  source = "./catch-all-lambda"

  prefix          = local.prefix
  short_prefix    = local.short_prefix
  api_domain_name = local.service_domain_name
  environment     = local.environment
  lambda_name    = module.lambda.lambda_function_name
  catch_all_lambda_name = module.catch_all_lambda.catch_all_lambda_name
  depends_on = [module.lambda]
}
