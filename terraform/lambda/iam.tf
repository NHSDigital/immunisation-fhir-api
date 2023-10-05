resource "aws_iam_role" lambda_role {
  name = "${var.short_prefix}-lambda-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
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


resource "aws_iam_role_policy" "lambda_role_policy" {
  name = "${var.prefix}-policy"
  role = aws_iam_role.lambda_role.id

  policy = <<EOF
{
     "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:PutLogEvents",
                "logs:GetLogEvents",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "*",
            "Resource": "arn:aws:dynamodb:*:*:table/${var.dynamodb_table_name}"
        }
    ]

}
EOF
}
