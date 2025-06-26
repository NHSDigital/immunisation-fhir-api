locals {
  forwarder_lambda_dir    = abspath("${path.root}/../backend")
  forwarder_source_path   = local.forwarder_lambda_dir
  forwarder_path_include  = ["**"]
  forwarder_path_exclude  = ["**/__pycache__/**"]
  forwarder_files_include = setunion([for f in local.forwarder_path_include : fileset(local.forwarder_source_path, f)]...)
  forwarder_files_exclude = setunion([for f in local.forwarder_path_exclude : fileset(local.forwarder_source_path, f)]...)
  forwarder_files         = sort(setsubtract(local.forwarder_files_include, local.forwarder_files_exclude))

  forwarder_dir_sha = sha1(join("", [for f in local.forwarder_files : filesha1("${local.forwarder_source_path}/${f}")]))
}

resource "aws_ecr_repository" "forwarder_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name = "${local.short_prefix}-forwarding-repo"
}

module "forwarding_docker_image" {
  source           = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version          = "7.21.1"
  create_ecr_repo  = false
  ecr_repo         = aws_ecr_repository.forwarder_lambda_repository.name
  docker_file_path = "batch.Dockerfile"
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
  source_path   = local.forwarder_lambda_dir
  triggers = {
    dir_sha = local.forwarder_dir_sha
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
            "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${local.immunisation_account_id}:function:${local.short_prefix}-forwarding_lambda"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "forwarding_lambda_exec_role" {
  name = "${local.short_prefix}-forwarding-lambda-exec-role"
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
  name = "${local.short_prefix}-forwarding-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${local.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-forwarding_lambda:*",
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.batch_prefix}-data-sources",
          "arn:aws:s3:::${local.batch_prefix}-data-sources/*"
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
          "${data.aws_s3_bucket.existing_destination_bucket.arn}",
          "${data.aws_s3_bucket.existing_destination_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [data.aws_kms_key.existing_lambda_encryption_key.arn,
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
        Resource = [data.aws_kms_key.existing_s3_encryption_key.arn,
        data.aws_kms_key.existing_dynamo_encryption_key.arn]
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
        Resource = ["arn:aws:dynamodb:*:*:table/${data.aws_dynamodb_table.events-dynamodb-table.name}",
        "arn:aws:dynamodb:*:*:table/${data.aws_dynamodb_table.events-dynamodb-table.name}/index/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.fifo_queue.arn
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
  function_name = "${local.short_prefix}-forwarding_lambda"
  role          = aws_iam_role.forwarding_lambda_exec_role.arn
  package_type  = "Image"
  architectures = ["x86_64"]
  image_uri     = module.forwarding_docker_image.image_uri
  timeout       = 900
  memory_size   = 2048
  ephemeral_storage {
    size = 1024
  }

  environment {
    variables = {
      SOURCE_BUCKET_NAME  = "${local.batch_prefix}-data-sources"
      ACK_BUCKET_NAME     = data.aws_s3_bucket.existing_destination_bucket.bucket
      DYNAMODB_TABLE_NAME = data.aws_dynamodb_table.events-dynamodb-table.name
      SQS_QUEUE_URL       = aws_sqs_queue.fifo_queue.url
    }
  }
  kms_key_arn = data.aws_kms_key.existing_lambda_encryption_key.arn
  depends_on = [
    aws_iam_role_policy_attachment.forwarding_lambda_exec_policy_attachment,
    aws_cloudwatch_log_group.forwarding_lambda_log_group
  ]

  reserved_concurrent_executions = 20
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
  name              = "/aws/lambda/${local.short_prefix}-forwarding_lambda"
  retention_in_days = 30
}
