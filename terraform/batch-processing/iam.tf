resource "aws_iam_role" batch_processing_lambda_role {
  name = "${var.short_prefix}-batch-processing-lambda-role"
  assume_role_policy = <<EOF
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": [
            "sts:AssumeRole"
          ],
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Effect": "Allow",
          "Sid": ""
        }
      ]
    }
    EOF
}

resource "aws_iam_policy" batch_processing_lambda_policy {
    name = "${var.short_prefix}-batch-processing-lambda-policy"
    policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:CopyObject",
        "s3:HeadObject"
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::${var.prefix}-batch-lambda-source",
        "arn:aws:s3:::${var.prefix}-batch-lambda-source/*"
      ]
    },
    {
      "Action": [
        "s3:ListBucket",
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:CopyObject",
        "s3:HeadObject"
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::${var.prefix}-batch-lambda-destination",
        "arn:aws:s3:::${var.prefix}-batch-lambda-destination/*"
      ]
    },
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "apig_lambda_role_to_policy" {
  role       = aws_iam_role.batch_processing_lambda_role.name
  policy_arn = aws_iam_policy.batch_processing_lambda_policy.arn
}

resource "aws_lambda_permission" "allow_terraform_bucket" {
   statement_id = "AllowExecutionFromS3Bucket"
   action = "lambda:InvokeFunction"
   function_name = "${aws_lambda_function.batch_processing_lambda.arn}"
   principal = "s3.amazonaws.com"
   source_arn = "${aws_s3_bucket.batch_lambda_source_bucket.arn}"
}
