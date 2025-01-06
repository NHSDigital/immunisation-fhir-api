resource "aws_dynamodb_table" "audit-table" {
    name         = "immunisation-batch-${local.env}-audit-table"
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

    global_secondary_index {
        name            = "filename_index"
        hash_key        = "filename"
        projection_type = "KEYS_ONLY"
    }

    point_in_time_recovery {
        enabled = local.environment == "prod" ? true : false
    }
    
}