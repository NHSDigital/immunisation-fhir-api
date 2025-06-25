resource "aws_s3_bucket" "batch_data_source_bucket" {
    bucket        = "${local.batch_prefix}-data-sources"
    force_destroy = local.is_temp
}

data "aws_iam_policy_document" "batch_data_source_bucket_policy" {
    source_policy_documents = [
        local.environment == "prod" ? templatefile("${local.policy_path}/s3_batch_source_policy_prod.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ):  templatefile("${local.policy_path}/s3_batch_source_policy.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ),
        
    ]
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
   bucket = aws_s3_bucket.batch_data_source_bucket.id
   policy = data.aws_iam_policy_document.batch_data_source_bucket_policy.json
}

# resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_source_encryption" {
#   bucket = aws_s3_bucket.batch_data_source_bucket.id

#   rule {
#     apply_server_side_encryption_by_default {
#       kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
#       sse_algorithm     = "aws:kms"
#     }
#   }
# }

resource "aws_s3_bucket_versioning" "source_versioning" {
  bucket = aws_s3_bucket.batch_data_source_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "datasources_lifecycle" {
  bucket = "${local.batch_prefix}-data-sources"
 
  rule {
    id     = "DeleteFinalFilesAfter7Days"
    status = "Enabled"
 
    filter {
      prefix = "archive/"
    }
 
    expiration {
      days = 7
    }
  }
}