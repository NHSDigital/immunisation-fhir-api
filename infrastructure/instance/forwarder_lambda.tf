locals {
  forwarder_lambda_name = "${local.short_prefix}-forwarding-lambda"
}

# IAM Role for Lambda
resource "aws_iam_role" "forwarding_lambda_exec_role" {
  name = "${local.forwarder_lambda_name}-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy for Lambda execution role to interact with logs, S3, KMS, and Kinesis.
resource "aws_iam_policy" "forwarding_lambda_exec_policy" {
  name = "${local.forwarder_lambda_name}-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.forwarder_lambda_name}:*",
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.batch_data_source_bucket.arn,
          "${aws_s3_bucket.batch_data_source_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.batch_data_destination_bucket.arn,
          "${aws_s3_bucket.batch_data_destination_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [
          data.aws_kms_key.existing_lambda_encryption_key.arn,
          data.aws_kms_key.existing_kinesis_encryption_key.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = [
          data.aws_kms_key.existing_s3_encryption_key.arn,
          data.aws_kms_key.existing_dynamo_encryption_key.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:ListStreams"
        ]
        Resource = local.kinesis_arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.events-dynamodb-table.arn,
          "${aws_dynamodb_table.events-dynamodb-table.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.fifo_queue.arn
      },
      {
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "forwarding_lambda_exec_policy_attachment" {
  role       = aws_iam_role.forwarding_lambda_exec_role.name
  policy_arn = aws_iam_policy.forwarding_lambda_exec_policy.arn
}

# Lambda Function
resource "aws_lambda_function" "forwarding_lambda" {
  function_name = local.forwarder_lambda_name
  role          = aws_iam_role.forwarding_lambda_exec_role.arn
  package_type  = "Image"
  architectures = ["x86_64"]
  image_uri     = var.recordforwarder_image_uri
  timeout       = 900
  memory_size   = 2048
  ephemeral_storage {
    size = 1024
  }

  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      SOURCE_BUCKET_NAME  = aws_s3_bucket.batch_data_source_bucket.bucket
      ACK_BUCKET_NAME     = aws_s3_bucket.batch_data_destination_bucket.bucket
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.events-dynamodb-table.name
      SQS_QUEUE_URL       = aws_sqs_queue.fifo_queue.url
      REDIS_HOST          = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT          = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
    }
  }
  kms_key_arn = data.aws_kms_key.existing_lambda_encryption_key.arn
  depends_on = [
    aws_iam_role_policy_attachment.forwarding_lambda_exec_policy_attachment,
    aws_cloudwatch_log_group.forwarding_lambda_log_group
  ]

  reserved_concurrent_executions = local.is_temp ? -1 : 20
}

resource "aws_lambda_event_source_mapping" "kinesis_event_source_mapping_forwarder_lambda" {
  event_source_arn  = local.kinesis_arn
  function_name     = aws_lambda_function.forwarding_lambda.function_name
  starting_position = "LATEST"
  batch_size        = 100
  enabled           = true

  depends_on = [aws_lambda_function.forwarding_lambda]
}

resource "aws_cloudwatch_log_group" "forwarding_lambda_log_group" {
  name              = "/aws/lambda/${local.forwarder_lambda_name}"
  retention_in_days = 30
}
