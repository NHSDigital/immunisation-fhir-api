resource "aws_iam_role" "dynamo_s3_access_role" {
  name = "imms-${local.resource_scope}-dynamo-s3-access-role"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          AWS : "arn:aws:iam::${var.dspp_core_account_id}:root"
        },
        Action : "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "dynamo_s3_access_policy" {
  name = "imms-${local.resource_scope}-dynamo_s3_access-policy"
  role = aws_iam_role.dynamo_s3_access_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ],
        Resource = [
          aws_dynamodb_table.delta-dynamodb-table.arn,
          "${aws_dynamodb_table.delta-dynamodb-table.arn}/index/*"
        ]
      }
    ]
  })
}
