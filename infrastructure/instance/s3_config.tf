resource "aws_s3_bucket" "batch_data_source_bucket" {
  bucket        = "${local.batch_prefix}-data-sources"
  force_destroy = local.is_temp
}

resource "aws_s3_bucket_public_access_block" "batch_data_source_bucket_public_access_block" {
  bucket = aws_s3_bucket.batch_data_source_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
  bucket = aws_s3_bucket.batch_data_source_bucket.bucket
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${var.dspp_core_account_id}:root"
        },
        Action : var.environment == "prod" ? [
          "s3:PutObject"
          ] : [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        Resource : [
          aws_s3_bucket.batch_data_source_bucket.arn,
          "${aws_s3_bucket.batch_data_source_bucket.arn}/*"
        ]
      },
      {
        Sid    = "HTTPSOnly"
        Effect = "Deny"
        Principal = {
          "AWS" : "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.batch_data_source_bucket.arn,
          "${aws_s3_bucket.batch_data_source_bucket.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
}

# resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_source_encryption" {
#   bucket = aws_s3_bucket.batch_data_source_bucket.bucket
#
#   rule {
#     apply_server_side_encryption_by_default {
#       kms_master_key_id = data.aws_kms_key.existing_s3_encryption_key.arn
#       sse_algorithm     = "aws:kms"
#     }
#   }
# }

resource "aws_s3_bucket_versioning" "source_versioning" {
  bucket = aws_s3_bucket.batch_data_source_bucket.bucket
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "datasources_lifecycle" {
  bucket = aws_s3_bucket.batch_data_source_bucket.bucket

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

  rule {
    id     = "DeleteExtendedAttributesFilesAfter7Days"
    status = "Enabled"

    filter {
      prefix = "extended-attributes-archive/"
    }
    expiration {
      days = 7
    }
  }
}

data "aws_iam_role" "existing_replication_role" {
  count = var.has_sub_environment_scope ? 0 : 1
  name  = "immunisation-batch-${var.environment}-replication"
}

data "aws_iam_policy_document" "replication_allow_destination" {
  count = var.has_sub_environment_scope ? 0 : 1

  statement {
    effect = "Allow"

    actions = [
      "s3:ReplicateObject",
      "s3:ReplicateDelete",
      "s3:ReplicateTags",
    ]

    resources = ["${aws_s3_bucket.batch_data_source_bucket.arn}/*"]
  }
}

resource "aws_iam_policy" "replication_allow_destination" {
  count  = var.has_sub_environment_scope ? 0 : 1
  name   = "${local.batch_prefix}-destination"
  policy = data.aws_iam_policy_document.replication_allow_destination[0].json
}

resource "aws_iam_role_policy_attachment" "replication_allow_destination" {
  count      = var.has_sub_environment_scope ? 0 : 1
  role       = data.aws_iam_role.existing_replication_role[0].name
  policy_arn = aws_iam_policy.replication_allow_destination[0].arn
}

resource "aws_s3_bucket_replication_configuration" "replication" {
  count  = var.has_sub_environment_scope ? 0 : 1
  role   = data.aws_iam_role.existing_replication_role[0].arn
  bucket = "immunisation-batch-${local.resource_scope}-data-sources"

  rule {
    id       = var.sub_environment
    priority = strcontains(var.sub_environment, "blue") ? 0 : 1
    status   = "Enabled"

    filter {
      prefix = ""
    }

    destination {
      bucket        = aws_s3_bucket.batch_data_source_bucket.arn
      storage_class = "STANDARD"

      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
    }
  }

  rule {
    id       = strcontains(var.sub_environment, "blue") ? replace(var.sub_environment, "blue", "green") : replace(var.sub_environment, "green", "blue")
    priority = strcontains(var.sub_environment, "blue") ? 1 : 0
    status   = "Disabled"

    filter {
      prefix = ""
    }

    destination {
      bucket        = strcontains(aws_s3_bucket.batch_data_source_bucket.arn, "blue") ? replace(aws_s3_bucket.batch_data_source_bucket.arn, "blue", "green") : replace(aws_s3_bucket.batch_data_source_bucket.arn, "green", "blue")
      storage_class = "STANDARD"

      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
    }
  }
}

resource "aws_s3_bucket" "batch_data_destination_bucket" {
  # Deliberately not using `local.batch_prefix` as we don't want separate blue / green destinations in prod.
  bucket        = "immunisation-batch-${local.resource_scope}-data-destinations"
  force_destroy = local.is_temp
}

resource "aws_s3_bucket_public_access_block" "batch_data_destination_bucket_public_access_block" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "batch_data_destination_bucket_policy" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${var.dspp_core_account_id}:root"
        },
        Action : var.environment == "prod" ? [
          "s3:ListBucket",
          "s3:GetObject",
          ] : [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:DeleteObject"
        ],
        Resource : [
          aws_s3_bucket.batch_data_destination_bucket.arn,
          "${aws_s3_bucket.batch_data_destination_bucket.arn}/*"
        ]
      },
      {
        Sid    = "HTTPSOnly"
        Effect = "Deny"
        Principal = {
          "AWS" : "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.batch_data_destination_bucket.arn,
          "${aws_s3_bucket.batch_data_destination_bucket.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
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

resource "aws_s3_bucket_lifecycle_configuration" "data_destinations" {
  bucket = aws_s3_bucket.batch_data_destination_bucket.id

  rule {
    id     = "DeleteFilesFromForwardedFile"
    status = "Enabled"

    filter {
      prefix = "forwardedFile/"
    }

    expiration {
      days = 14
    }
  }

  rule {
    id     = "DeleteFilesFromAckFolder"
    status = "Enabled"

    filter {
      prefix = "ack/"
    }

    expiration {
      days = 14
    }
  }
}

resource "aws_s3_bucket" "batch_config_bucket" {
  bucket = "imms-${local.resource_scope}-fhir-config"
}

resource "aws_s3_bucket_public_access_block" "batch_config_bucket_public_access_block" {
  bucket = aws_s3_bucket.batch_config_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "batch_config_bucket_policy" {
  bucket = aws_s3_bucket.batch_config_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "batch_config_bucket_policy"
    Statement = [
      {
        Sid    = "HTTPSOnly"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.batch_config_bucket.arn,
          "${aws_s3_bucket.batch_config_bucket.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
}
