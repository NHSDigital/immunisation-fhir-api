# Overall entry point into batch in prod. Files are forwarded into the appropriate blue / green bucket.
resource "aws_s3_bucket" "batch_data_source_bucket" {
  count  = var.blue_green_split ? 1 : 0
  bucket = "immunisation-batch-${var.environment}-data-sources"
}

resource "aws_s3_bucket_public_access_block" "batch_data_source_bucket_public_access_block" {
  count  = var.blue_green_split ? 1 : 0
  bucket = aws_s3_bucket.batch_data_source_bucket[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
  count  = var.blue_green_split ? 1 : 0
  bucket = aws_s3_bucket.batch_data_source_bucket[0].bucket
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${var.dspp_account_id}:root"
        },
        Action : [
          "s3:PutObject"
        ],
        Resource : [
          aws_s3_bucket.batch_data_source_bucket[0].arn,
          "${aws_s3_bucket.batch_data_source_bucket[0].arn}/*"
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
          aws_s3_bucket.batch_data_source_bucket[0].arn,
          "${aws_s3_bucket.batch_data_source_bucket[0].arn}/*",
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

resource "aws_s3_bucket_lifecycle_configuration" "datasources_lifecycle" {
  count  = var.blue_green_split ? 1 : 0
  bucket = aws_s3_bucket.batch_data_source_bucket[0].bucket

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

data "aws_iam_policy_document" "replication_assume_role" {
  count = var.blue_green_split ? 1 : 0

  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "replication" {
  count              = var.blue_green_split ? 1 : 0
  name               = "immunisation-batch-${var.environment}-replication"
  assume_role_policy = data.aws_iam_policy_document.replication_assume_role[0].json
}

data "aws_iam_policy_document" "replication_allow_source" {
  count = var.blue_green_split ? 1 : 0

  statement {
    effect = "Allow"

    actions = [
      "s3:GetReplicationConfiguration",
      "s3:ListBucket",
    ]

    resources = [aws_s3_bucket.batch_data_source_bucket[0].arn]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObjectVersionForReplication",
      "s3:GetObjectVersionAcl",
      "s3:GetObjectVersionTagging",
    ]

    resources = ["${aws_s3_bucket.batch_data_source_bucket[0].arn}/*"]
  }
}

resource "aws_iam_policy" "replication_allow_source" {
  count  = var.blue_green_split ? 1 : 0
  name   = "allow-replication-from-${var.environment}-data-sources"
  policy = data.aws_iam_policy_document.replication_allow_source[0].json
}

resource "aws_iam_role_policy_attachment" "replication_allow_source" {
  count      = var.blue_green_split ? 1 : 0
  role       = aws_iam_role.replication[0].name
  policy_arn = aws_iam_policy.replication_allow_source[0].arn
}
