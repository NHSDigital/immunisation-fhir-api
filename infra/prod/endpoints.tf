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
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    prefix_list_ids = [
      "pl-7ca54015",
      "pl-93a247fa",
      "pl-b3a742da"
    ]
  }

  # Egress rule to allow communication within the same security group
  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    self            = true
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
        Effect    = "Allow"
        Principal = {
          "AWS": [
            "*"
          ]
        },
        Action    = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "kms:Decrypt"
        ]
        Resource  = "*"
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
        Effect    = "Allow"
        Principal = {
          "AWS": [
            "*"
          ]
        },
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource  = "*"
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
        Principal =  "*",
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
        "Effect": "Allow",
        "Principal": "*",
        "Action": "*",
        "Resource": "*"
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

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = {
    Name = "immunisation-ecr-dkr-endpoint"
  }
}

resource "aws_vpc_endpoint" "cloud_watch" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
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
          "AWS":[
            "*"
        ]
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
        Principal = "*",
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey*"
        ],
        Resource = [
           "arn:aws:kms:eu-west-2:664418956997:key/4e643221-4cb8-49c5-9a78-ced991ff52ae",
				   "arn:aws:kms:eu-west-2:664418956997:key/d7b3c213-3c05-4caf-bb95-fdb2a6e533b1"
        ]
      }
    ]
  })
  tags = {
    Name = "immunisation-kms-endpoint"
  }
}

