data "aws_ec2_managed_prefix_list" "egress" {
  for_each = toset([
    "com.amazonaws.global.cloudfront.origin-facing",
    "com.amazonaws.eu-west-2.dynamodb",
    "com.amazonaws.eu-west-2.s3"
  ])

  name = each.value
}

resource "aws_security_group" "lambda_redis_sg" {
  vpc_id = data.aws_vpc.default.id
  name   = "immunisation-security-group"

  # Inbound rule to allow traffic only from the VPC CIDR block
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["172.31.0.0/16"]
  }

  # Outbound rules to specific AWS services using prefix lists
  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    prefix_list_ids = [
      for pl in data.aws_ec2_managed_prefix_list.egress : pl.id
    ]
  }

  # Egress rule to allow communication within the same security group
  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }
}

resource "aws_vpc_endpoint" "sqs_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
        },
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "kms:Decrypt"
        ]
        Resource = "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-sqs-endpoint"
  }
}

resource "aws_vpc_endpoint" "s3_endpoint" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  route_table_ids = [
    for rt in data.aws_route_tables.default_route_tables.ids : rt
  ]

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
        },
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:CopyObject",
          "s3:DeleteObject"
        ]
        Resource = "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "kinesis_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.kinesis-firehose"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
        },
        Action = [
          "firehose:ListDeliveryStreams",
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        Resource = "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-kinesis-endpoint"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.dynamodb"

  route_table_ids = [
    for rt in data.aws_route_tables.default_route_tables.ids : rt
  ]

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        "Effect" : "Allow",
        "Principal" : {
          AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
        },
        "Action" : "*",
        "Resource" : "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-dynamo-endpoint"
  }
}


resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-ecr-dkr-endpoint"
  }
}

resource "aws_vpc_endpoint" "cloud_watch" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-cloud-watch-endpoint"
  }
}


resource "aws_vpc_endpoint" "kinesis_stream_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.kinesis-streams"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
        },
        Action = [
          "kinesis:ListShards",
          "kinesis:ListStreams",
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ],
        Resource = "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-kinesis-streams-endpoint"
  }
}

# TODO - remove and use the key we manage in this Terraform workspace
data "aws_kms_key" "existing_lambda_env_encryption" {
  count = local.account != "prod" ? 1 : 0

  key_id = "648c8c6f-54bf-4b79-ad72-0be6e8d72423"
}

resource "aws_vpc_endpoint" "kms_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.kms"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${local.immunisation_account_id}:root"
        },
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey*"
        ],
        Resource = local.account == "prod" ? [
          aws_kms_key.lambda_env_encryption.arn,
          aws_kms_key.s3_shared_key.arn
          ] : [
          aws_kms_key.lambda_env_encryption.arn,
          aws_kms_key.s3_shared_key.arn,
          data.aws_kms_key.existing_lambda_env_encryption[0].arn
        ]
      }
    ]
  })

  tags = {
    Name = "immunisation-kms-endpoint"
  }
}

resource "aws_vpc_endpoint" "lambda_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.lambda"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-lambda-endpoint"
  }
}
