terraform {
  required_providers {
    aws = {
        source = "hashicorp/aws"
        version = "~> 3.5.0"
    }
  }
}

provider "aws" {
  region = "us-west-2"
}

resource "aws_api_gateway_rest_api" "immunisation_fhir_api" {
  name = "immunisation_fhir_api"
}

resource "aws_api_gateway_resource" "proxy_resource" {
  rest_api_id = aws_api_gateway_rest_api.immunisation_fhir_api.id
  parent_id   = aws_api_gateway_rest_api.immunisation_fhir_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy_method" {
  rest_api_id   = aws_api_gateway_rest_api.immunisation_fhir_api.id
  resource_id   = aws_api_gateway_resource.proxy_resource.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy_integration" {
  rest_api_id             = aws_api_gateway_rest_api.immunisation_fhir_api.id
  resource_id             = aws_api_gateway_resource.proxy_resource.id
  http_method             = aws_api_gateway_method.proxy_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.immunisation_fhir_lambda.invoke_arn
}

resource "aws_lambda_function" "immunisation_fhir_lambda" {
  function_name = "immunisation_fhir_lambda_function"
  role          = aws_iam_role.immunisation_fhir_lambda_role.arn
  handler       = "immunisation_fhir_lambda.handler"
  runtime       = "provided"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.immunisation_fhir_repository.repository_url}:latest"
  environment {
    variables = {
      IMMUNISATION_FHIR_TABLE_NAME = aws_dynamodb_table.immunisation_fhir_table.name
    }
  }
}

resource "aws_iam_role" "immunisation_fhir_lambda_role" {
  name = "immunisation_fhir_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "immunisation_fhir_lambda_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
  role       = aws_iam_role.immunisation_fhir_lambda_role.name
}

resource "aws_ecr_repository" "immunisation_fhir_repository" {
  name = "immunisation-fhir-repository"
}

resource "aws_dynamodb_table" "immunisation_fhir_table" {
  name     = "immunisation_fhir_table"
  hash_key = "nhsNumber"
  range_key = "fullUrl"

  attribute {
    name = "nhsNumber"
    type = "S"
  }
  attribute {
    name = "fullUrl"
    type = "S"
  }
}