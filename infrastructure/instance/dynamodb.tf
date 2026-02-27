resource "aws_dynamodb_table" "audit-table" {
  name                        = "immunisation-batch-${local.resource_scope}-audit-table"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "message_id"
  deletion_protection_enabled = !local.is_temp

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

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  global_secondary_index {
    name            = "filename_index"
    projection_type = "ALL"

    key_schema {
      attribute_name = "filename"
      key_type       = "HASH"
    }
  }

  global_secondary_index {
    name            = "queue_name_index"
    projection_type = "ALL"

    key_schema {
      attribute_name = "queue_name"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "status"
      key_type       = "RANGE"
    }
  }

  point_in_time_recovery {
    enabled = var.dynamodb_point_in_time_recovery_enabled
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_key.arn
  }
}

resource "aws_dynamodb_table" "delta-dynamodb-table" {
  name                        = "imms-${local.resource_scope}-delta"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "PK"
  deletion_protection_enabled = !local.is_temp

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "DateTimeStamp"
    type = "S"
  }

  attribute {
    name = "ImmsID"
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

  attribute {
    name = "SequenceNumber"
    type = "S"
  }

  ttl {
    attribute_name = "ExpiresAt"
    enabled        = true
  }

  global_secondary_index {
    name            = "SearchIndex"
    projection_type = "ALL"

    key_schema {
      attribute_name = "Operation"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "DateTimeStamp"
      key_type       = "RANGE"
    }
  }

  global_secondary_index {
    name            = "OperationSequenceIndex"
    projection_type = "ALL"

    key_schema {
      attribute_name = "Operation"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "DateTimeStamp"
      key_type       = "RANGE"
    }

    key_schema {
      attribute_name = "SequenceNumber"
      key_type       = "RANGE"
    }
  }

  global_secondary_index {
    name            = "SecondarySearchIndex"
    projection_type = "ALL"

    key_schema {
      attribute_name = "SupplierSystem"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "VaccineType"
      key_type       = "RANGE"
    }
  }

  global_secondary_index {
    name            = "ImmunisationIdIndex"
    projection_type = "ALL"

    key_schema {
      attribute_name = "ImmsID"
      key_type       = "HASH"
    }
  }

  point_in_time_recovery {
    enabled = var.dynamodb_point_in_time_recovery_enabled
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_key.arn
  }
}

resource "aws_dynamodb_table" "events-dynamodb-table" {
  name                        = "imms-${local.resource_scope}-imms-events"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "PK"
  stream_enabled              = true
  stream_view_type            = "NEW_IMAGE"
  deletion_protection_enabled = !local.is_temp

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
    projection_type = "ALL"

    key_schema {
      attribute_name = "PatientPK"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "PatientSK"
      key_type       = "RANGE"
    }
  }

  global_secondary_index {
    name            = "IdentifierGSI"
    projection_type = "ALL"

    key_schema {
      attribute_name = "IdentifierPK"
      key_type       = "HASH"
    }
  }

  point_in_time_recovery {
    enabled = var.dynamodb_point_in_time_recovery_enabled
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_key.arn
  }
}
