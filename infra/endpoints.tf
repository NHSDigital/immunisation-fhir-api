data "aws_ec2_managed_prefix_list" "egress" {
  for_each = toset([
    "com.amazonaws.global.cloudfront.origin-facing",
    "com.amazonaws.eu-west-2.dynamodb",
    "com.amazonaws.eu-west-2.s3"
  ])

  name = each.value
}

resource "aws_security_group" "lambda_redis_sg" {
  vpc_id = aws_vpc.default.id
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

  egress {
    description = "HTTPS outbound for PDS callout"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    self        = false
  }
}

resource "aws_vpc_endpoint" "sqs_endpoint" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
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
  vpc_id       = aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  route_table_ids = [aws_route_table.private.id]

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
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
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.kinesis-firehose"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = "*"
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
  vpc_id       = aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.dynamodb"

  route_table_ids = [aws_route_table.private.id]

  tags = {
    Name = "immunisation-dynamo-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-ecr-dkr-endpoint"
  }
}

resource "aws_vpc_endpoint" "cloud_watch" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-cloud-watch-endpoint"
  }
}


resource "aws_vpc_endpoint" "kinesis_stream_endpoint" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.kinesis-streams"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = "*"
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


resource "aws_vpc_endpoint" "kms_endpoint" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.kms"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = "*"
        },
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey*"
        ],
        Resource = [
          aws_kms_key.lambda_env_encryption.arn,
          aws_kms_key.s3_shared_key.arn
        ]
      }
    ]
  })

  tags = {
    Name = "immunisation-kms-endpoint"
  }
}

resource "aws_vpc_endpoint" "lambda_endpoint" {
  vpc_id            = aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.lambda"
  vpc_endpoint_type = "Interface"

  subnet_ids          = values(aws_subnet.private)[*].id
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-lambda-endpoint"
  }
}
