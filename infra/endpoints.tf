resource "aws_security_group" "lambda_redis_sg" {
  vpc_id = data.aws_vpc.default.id
  name   = "immunisation-security-group"
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
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
            "arn:aws:iam::${local.local_account_id}:root"
          ]
        },
        Action    = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "kms:Decrypt"
        ]
        Resource  = ["arn:aws:sqs:${var.aws_region}:${local.local_account_id}:${var.project_short_name}-int-metadata-queue.fifo",
          "arn:aws:sqs:${var.aws_region}:${local.local_account_id}:${var.project_short_name}-ref-metadata-queue.fifo",
          "arn:aws:sqs:${var.aws_region}:${local.local_account_id}:${var.project_short_name}-internal-dev-metadata-queue.fifo",
          "arn:aws:sqs:${var.aws_region}:${local.local_account_id}:${var.project_short_name}-pr-78-metadata-queue.fifo"]
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
            "arn:aws:iam::${local.local_account_id}:root"
          ]
        },
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource  = [
          "arn:aws:s3:::${var.project_name}-pr-78-data-sources",
          "arn:aws:s3:::${var.project_name}-pr-78-data-sources/*",
          "arn:aws:s3:::${var.project_name}-int-data-sources",
          "arn:aws:s3:::${var.project_name}-int-data-sources/*",
          "arn:aws:s3:::${var.project_name}-ref-data-sources",
          "arn:aws:s3:::${var.project_name}-ref-data-sources/*",
          "arn:aws:s3:::${var.project_name}-internal-dev-data-sources",
          "arn:aws:s3:::${var.project_name}-internal-dev-data-sources/*",
          "arn:aws:s3:::${var.project_name}-pr-78-data-destinations",
          "arn:aws:s3:::${var.project_name}-pr-78-data-destinations/*",
          "arn:aws:s3:::${var.project_name}-int-data-destinations",
          "arn:aws:s3:::${var.project_name}-int-data-destinations/*",
          "arn:aws:s3:::${var.project_name}-ref-data-destinations",
          "arn:aws:s3:::${var.project_name}-ref-data-destinations/*",
          "arn:aws:s3:::${var.project_name}-internal-dev-data-destinations",
          "arn:aws:s3:::${var.project_name}-internal-dev-data-destinations/*",
          "arn:aws:s3:::${aws_s3_bucket.batch_config_bucket.bucket}",
          "arn:aws:s3:::${aws_s3_bucket.batch_config_bucket.bucket}/*",
          "arn:aws:s3:::prod-${var.aws_region}-starport-layer-bucket/*"
        ]
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
          "AWS":[
            "arn:aws:iam::${local.local_account_id}:root"
        ]
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