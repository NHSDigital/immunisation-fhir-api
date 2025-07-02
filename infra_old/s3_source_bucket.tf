resource "aws_s3_bucket" "batch_data_source_bucket" {
  bucket        = "immunisation-batch-int-preprod-data-sources"
  force_destroy = local.is_temp
  tags = {
    "Environment" = "int"
    "Project"     = "immunisation"
    "Service"     = "fhir-api"
  }
}

data "aws_iam_policy_document" "batch_data_source_bucket_policy" {
  source_policy_documents = [
    templatefile("${local.policy_path}/s3_batch_source_policy.json", {
      "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
    }),
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

resource "aws_s3_bucket_lifecycle_configuration" "datasources_lifecycle" {
  bucket = "immunisation-batch-int-preprod-data-sources"

  rule {
    id     = "DeleteFilesAfter7Days"
    status = "Enabled"

    filter {
      prefix = "*"
    }

    expiration {
      days = 7
    }
  }
}
