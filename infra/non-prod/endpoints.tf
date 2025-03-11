resource "aws_security_group" "lambda_redis_sg" {
  vpc_id = data.aws_vpc.default.id
  name   = "immunisation-security-group"
  tags          = var.grafana_tags

  # Inbound rule to allow traffic only from the VPC CIDR block
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["172.31.0.0/16"]
  }

  egress  {
              cidr_blocks      = []
              from_port        = 0
              ipv6_cidr_blocks = []
              prefix_list_ids  = [
                  "pl-b3a742da",
                  "pl-93a247fa",
                  "pl-7ca54015",
                ]
              protocol         = "-1"
              security_groups  = []
              self             = true
              to_port          = 0
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
                AWS ="*"
        },
        Action    = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "kms:Decrypt"
        ]
        Resource  = "*",
      }
    ]
  })
  tags = merge(var.grafana_tags, {
    Name = "immunisation-sqs-endpoint"
  })
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
                AWS ="*"
        },
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject",
          "s3:CopyObject"
        ]
        Resource  = "*",
      }
    ]
  })
  tags = merge(var.grafana_tags, {
        Name = "immunisation-s3-endpoint"
  })
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
        Principal = "*",
        Action = [
          "firehose:ListDeliveryStreams",
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        Resource = "*"
      }
    ]
  })
  tags = merge(var.grafana_tags, {
    Name = "immunisation-kinesis-endpoint"
  })
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
  tags = merge(var.grafana_tags, {
    Name = "immunisation-dynamo-endpoint"
  })


}


resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = merge(var.grafana_tags, {
    Name = "immunisation-ecr-api-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = merge(var.grafana_tags, {
    Name = "immunisation-ecr-dkr-endpoint"
  })
}

resource "aws_vpc_endpoint" "cloud_watch" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true
  tags = merge(var.grafana_tags, {
    Name = "immunisation-cloud-watch-endpoint"
  })
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
                AWS ="*"
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
  tags = merge(var.grafana_tags, {
    Name = "immunisation-kinesis-streams-endpoint"
  })
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
           "arn:aws:kms:eu-west-2:345594581768:key/648c8c6f-54bf-4b79-ad72-0be6e8d72423",
           "arn:aws:kms:eu-west-2:345594581768:key/9bbfbfd9-1745-4325-a9b7-33d1f6be89c1"
        ]
      }
    ]
  })
  tags = merge(var.grafana_tags, {    Name = "immunisation-kms-endpoint"
  })
}


resource "aws_vpc_endpoint" "lambda_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.lambda"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  tags = merge(var.grafana_tags, {
    Name = "immunisation-lambda-endpoint"
  })
}