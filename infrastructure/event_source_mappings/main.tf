terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
  }
  backend "s3" {
    region       = "eu-west-2"
    key          = "event-source-mappings/state"
    use_lockfile = true
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = local.resource_scope
      Service     = var.service
    }
  }
}

locals {
  resource_scope      = var.has_sub_environment_scope ? var.sub_environment : var.environment
  short_prefix        = "${var.project_short_name}-${var.sub_environment}"
  events_table_name   = "imms-${local.resource_scope}-imms-events"
  id_sync_queue_name  = "imms-${local.resource_scope}-id-sync-queue"
  delta_lambda_name   = "${local.short_prefix}-delta-lambda"
  delta_dlq_name      = "${local.short_prefix}-delta-dlq"
  id_sync_lambda_name = "${local.short_prefix}-id-sync-lambda"
}

data "aws_dynamodb_table" "events" {
  name = local.events_table_name
}

data "aws_sqs_queue" "delta_dlq" {
  name = local.delta_dlq_name
}

data "aws_sqs_queue" "id_sync" {
  name = local.id_sync_queue_name
}

data "aws_lambda_function" "delta" {
  function_name = local.delta_lambda_name
}

data "aws_lambda_function" "id_sync" {
  function_name = local.id_sync_lambda_name
}

resource "aws_lambda_event_source_mapping" "delta_trigger" {
  event_source_arn  = data.aws_dynamodb_table.events.stream_arn
  function_name     = data.aws_lambda_function.delta.function_name
  starting_position = "TRIM_HORIZON"

  destination_config {
    on_failure {
      destination_arn = data.aws_sqs_queue.delta_dlq.arn
    }
  }

  maximum_retry_attempts = 0
}

resource "aws_lambda_event_source_mapping" "id_sync_sqs_trigger" {
  event_source_arn = data.aws_sqs_queue.id_sync.arn
  function_name    = data.aws_lambda_function.id_sync.arn

  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
}
