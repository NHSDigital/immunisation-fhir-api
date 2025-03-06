resource "aws_dynamodb_table" "events-dynamodb-int-table" {
    name         = "imms-int-imms-events"
    billing_mode = "PAY_PER_REQUEST"
    hash_key     = "PK"
    stream_enabled = true
    stream_view_type  = "NEW_IMAGE"

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

  tags = merge(var.grafana_tags, {
        NHSE-Enable-Dynamo-Backup = "True"
    })

    global_secondary_index {
        name               = "PatientGSI"
        hash_key           = "PatientPK"
        range_key          = "PatientSK"
        projection_type    = "ALL"
    }

    global_secondary_index {
        name               = "IdentifierGSI"
        hash_key           = "IdentifierPK"
        projection_type    = "ALL"
    }
     
    server_side_encryption {
        enabled = true
        kms_key_arn = aws_kms_key.dynamodb_encryption.arn
    }
}

resource "aws_dynamodb_table" "events-dynamodb-ref-table" {
    name         = "imms-ref-imms-events"
    billing_mode = "PAY_PER_REQUEST"
    hash_key     = "PK"
    stream_enabled = true
    stream_view_type  = "NEW_IMAGE"

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

  tags = merge(var.grafana_tags, {
        NHSE-Enable-Dynamo-Backup = "True"
    })

    global_secondary_index {
        name               = "PatientGSI"
        hash_key           = "PatientPK"
        range_key          = "PatientSK"
        projection_type    = "ALL"
    }

    global_secondary_index {
        name               = "IdentifierGSI"
        hash_key           = "IdentifierPK"
        projection_type    = "ALL"
    }
     
    server_side_encryption {
        enabled = true
        kms_key_arn = aws_kms_key.dynamodb_encryption.arn
    }
}

resource "aws_dynamodb_table" "events-dynamodb-table" {
    name         = "imms-internal-dev-imms-events"
    billing_mode = "PAY_PER_REQUEST"
    hash_key     = "PK"
    stream_enabled = true
    stream_view_type  = "NEW_IMAGE"

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

   tags = merge(var.grafana_tags, {       NHSE-Enable-Dynamo-Backup = "True"
    })

    global_secondary_index {
        name               = "PatientGSI"
        hash_key           = "PatientPK"
        range_key          = "PatientSK"
        projection_type    = "ALL"
    }

    global_secondary_index {
        name               = "IdentifierGSI"
        hash_key           = "IdentifierPK"
        projection_type    = "ALL"
    }
     
    server_side_encryption {
        enabled = true
        kms_key_arn = aws_kms_key.dynamodb_encryption.arn
    }
}