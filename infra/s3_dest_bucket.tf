locals {
    policy_path = "${path.root}/policies"
    env         = terraform.workspace
    batch_prefix = "immunisation-batch-${local.env}"
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.env)) > 0
    }

resource "aws_s3_bucket" "batch_data_destination_bucket" {
    bucket        = "${local.batch_prefix}-data-destinations"
    force_destroy = local.is_temp
}

data "aws_iam_policy_document" "batch_data_destination_bucket_policy" {
    source_policy_documents = [
        local.environment == "prod" ? templatefile("${local.policy_path}/s3_batch_dest_policy_prod.json", {
            "bucket-name" : aws_s3_bucket.batch_data_destination_bucket.bucket
        } ):  templatefile("${local.policy_path}/s3_batch_dest_policy.json", {
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