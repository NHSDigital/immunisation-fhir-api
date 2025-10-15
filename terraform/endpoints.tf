/// This file creates all lambdas needed for each endpoint plus api-gateway

locals {
  policy_path = "${path.root}/policies"
}

# Select the Policy folder
data "aws_iam_policy_document" "logs_policy_document" {
  source_policy_documents = [templatefile("${local.policy_path}/log.json", {})]
}
module "get_status" {
  source        = "./modules/lambda"
  prefix        = local.prefix
  short_prefix  = local.short_prefix
  function_name = "get_status"
  image_uri     = module.docker_image.image_uri
  policy_json   = data.aws_iam_policy_document.logs_policy_document.json
}

locals {
  imms_endpoints = [
    "get_imms", "create_imms", "update_imms", "search_imms", "delete_imms", "not_found"
  ]
  imms_table_name = aws_dynamodb_table.events-dynamodb-table.name
  imms_lambda_env_vars = {
    "DYNAMODB_TABLE_NAME"    = local.imms_table_name,
    "IMMUNIZATION_ENV"       = local.resource_scope,
    "IMMUNIZATION_BASE_PATH" = strcontains(var.sub_environment, "pr-") ? "immunisation-fhir-api/FHIR/R4-${var.sub_environment}" : "immunisation-fhir-api/FHIR/R4"
    # except for prod and ref, any other env uses PDS int environment
    "PDS_ENV"              = var.pds_environment
    "PDS_CHECK_ENABLED"    = tostring(var.pds_check_enabled)
    "SPLUNK_FIREHOSE_NAME" = module.splunk.firehose_stream_name
    "SQS_QUEUE_URL"        = "https://sqs.eu-west-2.amazonaws.com/${var.immunisation_account_id}/${local.short_prefix}-ack-metadata-queue.fifo"
    "REDIS_HOST"           = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
    "REDIS_PORT"           = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
  }
}
data "aws_iam_policy_document" "imms_policy_document" {
  source_policy_documents = [
    templatefile("${local.policy_path}/dynamodb.json", {
      "dynamodb_table_name" : local.imms_table_name
    }),
    templatefile("${local.policy_path}/log.json", {}),
    templatefile("${local.policy_path}/lambda_to_sqs.json", {
      "local_account" : var.immunisation_account_id
      "queue_prefix" : local.short_prefix
    }),
    templatefile("${local.policy_path}/dynamo_key_access.json", {
      "dynamo_encryption_key" : data.aws_kms_key.existing_dynamo_encryption_key.arn
    }),
    templatefile("${local.policy_path}/log_kinesis.json", {
      "kinesis_stream_name" : module.splunk.firehose_stream_name
    }),
    templatefile("${local.policy_path}/secret_manager.json", {
      "account_id" : data.aws_caller_identity.current.account_id
    }),
    file("${local.policy_path}/ec2_network_interfaces.json")
  ]
}

data "aws_iam_policy_document" "imms_data_quality_s3_doc" {
  source_policy_documents = [
    templatefile("${local.policy_path}/s3_data_quality_access.json", {
      s3_bucket_arn = aws_s3_bucket.data_quality_reports_bucket.arn
      kms_key_arn    = data.aws_kms_key.existing_s3_encryption_key.arn
    })
  ]
}

resource "aws_iam_policy" "imms_s3_kms_policy" {
  name   = "${local.short_prefix}-s3-kms-policy"
  policy = data.aws_iam_policy_document.imms_data_quality_s3_doc.json
}

module "imms_event_endpoint_lambdas" {
  source = "./modules/lambda"
  count  = length(local.imms_endpoints)

  prefix                 = local.prefix
  short_prefix           = local.short_prefix
  function_name          = local.imms_endpoints[count.index]
  image_uri              = module.docker_image.image_uri
  policy_json            = data.aws_iam_policy_document.imms_policy_document.json
  environment_variables  = local.imms_lambda_env_vars
  vpc_subnet_ids         = local.private_subnet_ids
  vpc_security_group_ids = [data.aws_security_group.existing_securitygroup.id]
}


# Attach data quality report S3 bucket and KMS policy only to "create_imms" and "update_imms" endpoints
resource "aws_iam_role_policy_attachment" "attach_data_quality_s3_to_specific_lambdas" {
  for_each = {
    for i, mod in module.imms_event_endpoint_lambdas :
    local.imms_endpoints[i] => mod
    if local.imms_endpoints[i] == "create_imms" || local.imms_endpoints[i] == "update_imms"
  }

  role       = each.value.lambda_role_name
  policy_arn = aws_iam_policy.imms_s3_kms_policy.arn
}

locals {
  # Mapping outputs with each called lambda
  imms_lambdas = {
    for lambda in module.imms_event_endpoint_lambdas[*] : lambda.function_name =>
    {
      lambda_arn : lambda.lambda_arn
    }
  }

  status_lambda_route = [module.get_status.function_name]
  #Constructing routes for event lambdas
  endpoint_routes = keys(local.imms_lambdas)

  #Concating routes for  status and event lambdas
  routes = concat(local.status_lambda_route, local.endpoint_routes)
}

locals {
  oas_parameters = {
    get_event      = local.imms_lambdas["${local.short_prefix}_get_imms"]
    post_event     = local.imms_lambdas["${local.short_prefix}_create_imms"]
    update_event   = local.imms_lambdas["${local.short_prefix}_update_imms"]
    delete_event   = local.imms_lambdas["${local.short_prefix}_delete_imms"]
    search_event   = local.imms_lambdas["${local.short_prefix}_search_imms"]
    not_found      = local.imms_lambdas["${local.short_prefix}_not_found"]
    get_status_arn = module.get_status.lambda_arn

  }
  oas = templatefile("${path.root}/oas.yaml", local.oas_parameters)
}
output "oas" {
  value = local.oas
}

module "api_gateway" {
  source = "./modules/api_gateway"

  prefix                  = local.prefix
  short_prefix            = local.short_prefix
  zone_id                 = data.aws_route53_zone.project_zone.zone_id
  api_domain_name         = local.service_domain_name
  environment             = var.environment
  sub_environment         = var.sub_environment
  oas                     = local.oas
  aws_region              = var.aws_region
  immunisation_account_id = var.immunisation_account_id
  csoc_account_id         = var.csoc_account_id
}

resource "aws_lambda_permission" "api_gw" {
  count         = length(local.routes)
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = local.routes[count.index]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${module.api_gateway.api_execution_arn}/*/*"
}
