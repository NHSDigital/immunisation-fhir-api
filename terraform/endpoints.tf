/// This file creates all lambdas needed for each endpoint plus api-gateway

locals {
    policy_path = "${path.root}/policies"
    domain_name_url = "https://${local.service_domain_name}"
}

data "aws_iam_policy_document" "logs_policy_document" {
    source_policy_documents = [templatefile("${local.policy_path}/log.json", {} )]
}

data "aws_iam_policy_document" "batch_policy_document" {
    source_policy_documents = [
        templatefile("${local.policy_path}/dynamodb.json", {
            "dynamodb_table_name" : local.imms_table_name
        } ),
        templatefile("${local.policy_path}/log.json", {} ),
        templatefile("${local.policy_path}/log_kinesis.json", {
            "kinesis_stream_name" : module.splunk.firehose_stream_name
        } ),
        templatefile("${local.policy_path}/secret_manager.json", {
            "account_id": data.aws_caller_identity.current.account_id
        }),
        templatefile("${local.policy_path}/batch_kinesis.json", {
            "account_id": local.local_account_id 
            "env": local.environment
            "kms_key": data.aws_kms_key.existing_kinesis_encryption_key.arn
        })
    ]
}
module "get_status" {
    source        = "./lambda"
    prefix        = local.prefix
    short_prefix  = local.short_prefix
    function_name = "get_status"
    image_uri     = module.docker_image.image_uri
    policy_json   = data.aws_iam_policy_document.logs_policy_document.json
}

module "batch_processing" {
    source        = "./lambda"
    prefix        = local.prefix
    short_prefix  = local.short_prefix
    function_name = "batch_processing"
    image_uri     = module.docker_image.image_uri
    policy_json   = data.aws_iam_policy_document.batch_policy_document.json
    environments  = local.imms_lambda_env_vars
}

locals {
    imms_endpoints = [
        "get_imms", "create_imms", "update_imms", "search_imms", "delete_imms", "not_found"
    ]
    imms_table_name      = aws_dynamodb_table.events-dynamodb-table.name
    imms_lambda_env_vars = {
        "DYNAMODB_TABLE_NAME"    = local.imms_table_name,
        "IMMUNIZATION_ENV"       = local.environment,
        "IMMUNIZATION_BASE_PATH" = strcontains(local.environment, "pr-") ? "immunisation-fhir-api-${local.environment}" : "immunisation-fhir-api"
        # except for prod and ref, any other env uses PDS int environment
        "PDS_ENV"                = local.environment == "prod" ? "prod" : local.environment == "ref" ? "ref" : "int",
        "SPLUNK_FIREHOSE_NAME"   = module.splunk.firehose_stream_name
    }
}
data "aws_iam_policy_document" "imms_policy_document" {
    source_policy_documents = [
        templatefile("${local.policy_path}/dynamodb.json", {
            "dynamodb_table_name" : local.imms_table_name
        } ),
        templatefile("${local.policy_path}/log.json", {} ),
        templatefile("${local.policy_path}/log_kinesis.json", {
            "kinesis_stream_name" : module.splunk.firehose_stream_name
        } ),
        templatefile("${local.policy_path}/secret_manager.json", {
            "account_id": data.aws_caller_identity.current.account_id
        })
    ]
}

module "imms_event_endpoint_lambdas" {
    source = "./lambda"
    count  = length(local.imms_endpoints)

    prefix        = local.prefix
    short_prefix  = local.short_prefix
    function_name = local.imms_endpoints[count.index]
    image_uri     = module.docker_image.image_uri
    policy_json   = data.aws_iam_policy_document.imms_policy_document.json
    environments  = local.imms_lambda_env_vars
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
    endpoint_routes     = keys(local.imms_lambdas)

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
    source = "./api_gateway"

    prefix          = local.prefix
    short_prefix    = local.short_prefix
    zone_id         = data.aws_route53_zone.project_zone.zone_id
    api_domain_name = local.service_domain_name
    environment     = local.environment
    oas             = local.oas
}

resource "aws_lambda_permission" "api_gw" {
    count         = length(local.routes)
    statement_id  = "AllowExecutionFromAPIGateway"
    action        = "lambda:InvokeFunction"
    function_name = local.routes[count.index]
    principal     = "apigateway.amazonaws.com"
    source_arn    = "${module.api_gateway.api_execution_arn}/*/*"
}

resource "aws_lambda_event_source_mapping" "kinesis_event_source_mapping_batch_lambda" {
    event_source_arn  = data.aws_kinesis_stream.existing_kinesis_stream.arn
    function_name     = module.batch_processing.function_name
    starting_position = "LATEST"
    batch_size        = 10
    enabled           = true
 }