# TODO - move to instance terraform
resource "aws_dynamodb_table" "audit-table" {
  name         = "immunisation-batch-${local.environment}-audit-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  attribute {
    name = "filename"
    type = "S"
  }

  attribute {
    name = "queue_name"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "filename_index"
    hash_key        = "filename"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "queue_name_index"
    hash_key        = "queue_name"
    range_key       = "status"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = local.environment == "prod"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_encryption.arn
  }

  tags = {
    "Environment" = local.environment
    "Project"     = "immunisation"
    "Service"     = "fhir-api"
  }
}
