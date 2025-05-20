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
    kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_key.arn
  }
}

resource "aws_dynamodb_table" "delta-dynamodb-table" {
  name         = "imms-${local.environment}-delta"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "DateTimeStamp"
    type = "S"
  }

  attribute {
    name = "Operation"
    type = "S"
  }

  attribute {
    name = "VaccineType"
    type = "S"
  }

  attribute {
    name = "SupplierSystem"
    type = "S"
  }

  ttl {
    attribute_name = "ExpiresAt"
    enabled        = true
  }

  global_secondary_index {
    name            = "SearchIndex"
    hash_key        = "Operation"
    range_key       = "DateTimeStamp"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "SecondarySearchIndex"
    hash_key        = "SupplierSystem"
    range_key       = "VaccineType"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = local.environment == "prod"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_key.arn
  }
}

resource "aws_dynamodb_table" "events-dynamodb-table" {
  name             = "imms-${local.environment}-imms-events"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "PK"
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "PatientPK"
    type = "S"
  }
  attribute {
    name = "PatientSK"
    type = "S"
  }
  attribute {
    name = "IdentifierPK"
    type = "S"
  }

  tags = {
    NHSE-Enable-Dynamo-Backup = "True"
  }

  global_secondary_index {
    name            = "PatientGSI"
    hash_key        = "PatientPK"
    range_key       = "PatientSK"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "IdentifierGSI"
    hash_key        = "IdentifierPK"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = local.environment == "prod"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_key.arn
  }
}
