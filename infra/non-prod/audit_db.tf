resource "aws_dynamodb_table" "audit-table-int" {
    name         = "immunisation-batch-int-audit-table"
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
        name               = "queue_name_index"
        hash_key           = "queue_name"
        range_key          = "status"
        projection_type    = "ALL"
    }

    server_side_encryption {
        enabled = true
        kms_key_arn = aws_kms_key.dynamodb_encryption.arn
    }
}

resource "aws_dynamodb_table" "audit-table-ref" {
    name         = "immunisation-batch-ref-audit-table"
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
        name               = "queue_name_index"
        hash_key           = "queue_name"
        range_key          = "status"
        projection_type    = "ALL"
    }

    server_side_encryption {
        enabled = true
        kms_key_arn = aws_kms_key.dynamodb_encryption.arn
    }
}

resource "aws_dynamodb_table" "audit-table" {
    name         = "immunisation-batch-internal-dev-audit-table"
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
        projection_type = "KEYS_ONLY"
    }

    server_side_encryption {
        enabled = true
        kms_key_arn = aws_kms_key.dynamodb_encryption.arn
    }
}