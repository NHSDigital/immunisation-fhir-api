# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  forwarder_lambda_dir     = abspath("${path.root}/../../lambdas/recordforwarder")
  forwarder_lambda_files   = fileset(local.forwarder_lambda_dir, "**")
  forwarder_lambda_dir_sha = sha1(join("", [for f in local.forwarder_lambda_files : filesha1("${local.forwarder_lambda_dir}/${f}")]))
  forwarder_lambda_name    = "${local.short_prefix}-forwarding-lambda"
}

resource "aws_ecr_repository" "forwarder_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.short_prefix}-forwarding-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "forwarding_docker_image" {
  source           = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version          = "8.4.0"
  docker_file_path = "./recordforwarder/Dockerfile"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.forwarder_lambda_repository.name
  ecr_repo_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 2 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 2
        }
        action = {
          type = "expire"
        }
      }
    ]
  })

  platform      = "linux/amd64"
  use_image_tag = false
  source_path   = abspath("${path.root}/../../lambdas")
  triggers = {
    dir_sha        = local.forwarder_lambda_dir_sha
    shared_dir_sha = local.shared_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "forwarder_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.forwarder_lambda_repository.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Sid" : "LambdaECRImageRetrievalPolicy",
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : [
          "ecr:BatchGetImage",
          "ecr:DeleteRepositoryPolicy",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:SetRepositoryPolicy"
        ],
        "Condition" : {
          "StringLike" : {
            "aws:sourceArn" : "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.forwarder_lambda_name}"
          }
        }
      }
    ]
  })
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
  image_uri     = module.forwarding_docker_image.image_uri
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
