locals {
    policy_path = "${path.root}/policies"
    env         = terraform.workspace
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.env)) > 0
    }

resource "aws_s3_bucket" "batch_data_destination_int_bucket" {
    bucket        = "immunisation-batch-int-data-destinations"
    force_destroy = local.is_temp
    tags          = {
        "Environment" = "int"
        "Project"     = "immunisation"
        "Service"     = "fhir-api"
    }
}

data "aws_iam_policy_document" "batch_data_destination_int_bucket_policy" {
    source_policy_documents = [
        templatefile("${local.policy_path}/s3_batch_dest_policy.json", {
            "bucket-name" : aws_s3_bucket.batch_data_destination_int_bucket.bucket
        } ),
    ]
}

resource "aws_s3_bucket_policy" "batch_data_destination_int_bucket_policy" {
   bucket = aws_s3_bucket.batch_data_destination_int_bucket.id
   policy = data.aws_iam_policy_document.batch_data_destination_int_bucket_policy.json
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_destination_int_encryption" {
  bucket = aws_s3_bucket.batch_data_destination_int_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}


resource "aws_s3_bucket" "batch_data_destination_ref_bucket" {
    bucket        = "immunisation-batch-ref-data-destinations"
    force_destroy = local.is_temp
    tags          = {
        "Environment" = "ref"
        "Project"     = "immunisation"
        "Service"     = "fhir-api"
    }
}

data "aws_iam_policy_document" "batch_data_destination_ref_bucket_policy" {
    source_policy_documents = [
        templatefile("${local.policy_path}/s3_batch_dest_policy.json", {
            "bucket-name" : aws_s3_bucket.batch_data_destination_ref_bucket.bucket
        } ),
    ]
}

resource "aws_s3_bucket_policy" "batch_data_destination_ref_bucket_policy" {
   bucket = aws_s3_bucket.batch_data_destination_ref_bucket.id
   policy = data.aws_iam_policy_document.batch_data_destination_ref_bucket_policy.json
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_destination_ref_encryption" {
  bucket = aws_s3_bucket.batch_data_destination_ref_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket" "batch_data_destination_bucket" {
    bucket        = "immunisation-batch-internal-dev-data-destinations"
    force_destroy = local.is_temp
    tags          = {
        "Environment" = "internal-dev"
        "Project"     = "immunisation"
        "Service"     = "fhir-api"
    }
}

data "aws_iam_policy_document" "batch_data_destination_bucket_policy" {
    source_policy_documents = [
        templatefile("${local.policy_path}/s3_batch_dest_policy.json", {
            "bucket-name" : aws_s3_bucket.batch_data_destination_bucket.bucket
        } ),
    ]
}

resource "aws_s3_bucket_policy" "batch_data_destination_bucket_policy" {
   bucket = aws_s3_bucket.batch_data_destination_bucket.id
   policy = data.aws_iam_policy_document.batch_data_destination_bucket_policy.json
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_destination_encryption" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}



