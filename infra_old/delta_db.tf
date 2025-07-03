resource "aws_dynamodb_table" "delta-dynamodb-table" {
  name         = "imms-int-delta"
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
    enabled = true
  }
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_encryption.arn
  }

  tags = {
    "Environment" = "int"
    "Project"     = "immunisation"
    "Service"     = "fhir-api"
  }
}
