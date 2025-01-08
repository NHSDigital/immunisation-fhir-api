resource "aws_dynamodb_table" "events-dynamodb-table" {
    name         = "imms-${local.env}-imms-events"
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

    tags = {
        NHSE-Enable-Dynamo-Backup = "True"
    }

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
    
    point_in_time_recovery {
        enabled = local.environment == "prod" ? true : false
    }
    server_side_encryption {
        enabled = true
        kms_key_arn = data.aws_kms_key.existing_dynamo_encryption_arn.arn
    }
}