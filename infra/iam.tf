resource "aws_iam_role" "kinesis_role" {
  name = "kinesis-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "kinesis.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "kinesis_kms_policy" {
  name        = "kinesis-kms-policy"
  description = "Allow Kinesis to use the KMS key"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey*",
        "kms:ReEncrypt*",
        "kms:DescribeKey"
      ]
      Resource = aws_kms_key.kinesis_stream_encryption.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "kinesis_role_policy_attachment" {
  role       = aws_iam_role.kinesis_role.name
  policy_arn = aws_iam_policy.kinesis_kms_policy.arn
}

resource "aws_iam_role" "auto_ops" {
  name = "auto-ops"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      },
      {
        Sid    = "",
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${var.build_agent_account_id}:role/build-agent"
        },
        Action = "sts:AssumeRole"
      },
      {
        Sid    = "",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${var.imms_account_id}:oidc-provider/token.actions.githubusercontent.com"
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" : "sts.amazonaws.com"
          },
          StringLike = {
            "token.actions.githubusercontent.com:sub" : "repo:NHSDigital/immunisation-fhir-api:*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "auto_ops" {
  name   = "auto-ops"
  policy = file("auto_ops_policy.json")
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.auto_ops.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "custom_auto_ops" {
  role       = aws_iam_role.auto_ops.name
  policy_arn = aws_iam_policy.auto_ops.arn
}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "2b18947a6a9fc7764fd8b5fb18a863b0c6dac24f"
  ]
}
