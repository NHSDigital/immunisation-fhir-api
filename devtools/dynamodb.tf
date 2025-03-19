terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 5"
        }
    }
    backend "local" {
        path = ".terraform/local.tfstate"
    }
}

provider "aws" {
    region = "us-east-1"
    skip_region_validation = true

    endpoints {
        sts      = "http://localhost:4566"
        dynamodb = "http://localhost:4566"
    }
}

locals {
    short_prefix = "local"
}

resource "aws_dynamodb_table" "events-dynamodb-table" {
    name         = "${local.short_prefix}-imms-events"  
    billing_mode = "PAY_PER_REQUEST"  
    hash_key     = "PK"

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

    global_secondary_index {
        name               = "PatientGSI"
        hash_key           = "PatientPK"
        range_key          = "PatientSK"
        projection_type    = "INCLUDE"
        non_key_attributes = ["Resource"]
    }
}
