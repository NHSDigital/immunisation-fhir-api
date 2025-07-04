data "aws_iam_policy_document" "firehose_assume_role" {
    statement {
        effect = "Allow"

        principals {
            type        = "Service"
            identifiers = ["firehose.amazonaws.com"]
        }

        actions = ["sts:AssumeRole"]
    }
}

data "aws_iam_policy_document" "firehose_policy" {
    statement {
        effect  = "Allow"
        actions = [
            "s3:PutObject",
            "s3:AbortMultipartUpload",
            "s3:ListBucket",
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
        ]
        resources = [
            "${aws_s3_bucket.failed_logs_backup.arn}/*",
            aws_s3_bucket.failed_logs_backup.arn,
            "arn:aws:logs:*:*:*"

        ]
    }
}
resource "aws_iam_role_policy" "firehose_policy" {
    name   = "${local.prefix}-firehose-role-policy"
    policy = data.aws_iam_policy_document.firehose_policy.json
    role   = aws_iam_role.firehose_role.id
}


resource "aws_iam_role" "firehose_role" {
    name               = "${local.prefix}-firehose"
    assume_role_policy = data.aws_iam_policy_document.firehose_assume_role.json
}