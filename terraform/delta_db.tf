resource "aws_dynamodb_table" "delta-dynamodb-table" {
    name         = "${local.short_prefix}-delta"
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

    ttl {
          attribute_name = "ExpiresAt"
          enabled        = true
    }

    global_secondary_index {
        name               = "SearchIndex"
        hash_key           = "Operation"
        range_key          = "DateTimeStamp"
        projection_type    = "ALL"
    }
}