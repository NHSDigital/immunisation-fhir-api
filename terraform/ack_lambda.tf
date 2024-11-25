# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  ack_lambda_dir = abspath("${path.root}/../ack_backend")
  ack_lambda_files         = fileset(local.ack_lambda_dir, "**")
  ack_lambda_dir_sha       = sha1(join("", [for f in local.ack_lambda_files : filesha1("${local.ack_lambda_dir}/${f}")]))
}


resource "aws_ecr_repository" "ack_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name = "${local.short_prefix}-ack-repo"
}

# Module for building and pushing Docker image to ECR
module "ack_processor_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.ack_lambda_repository.name
  ecr_repo_lifecycle_policy = jsonencode({
    "rules" : [
      {
        "rulePriority" : 1,
        "description" : "Keep only the last 2 images",
        "selection" : {
          "tagStatus" : "any",
          "countType" : "imageCountMoreThan",
          "countNumber" : 2
        },
        "action" : {
          "type" : "expire"
        }
      }
    ]
  })

  platform      = "linux/amd64"
  use_image_tag = false
  source_path   = local.ack_lambda_dir
  triggers = {
    dir_sha = local.ack_lambda_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "ack_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.ack_lambda_repository.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Sid": "LambdaECRImageRetrievalPolicy",
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": [
          "ecr:BatchGetImage",
          "ecr:DeleteRepositoryPolicy",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:SetRepositoryPolicy"
        ],
        "Condition": {
          "StringLike": {
            "aws:sourceArn": "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}-ack-lambda"
          }
        }
      }
  ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "ack_lambda_exec_role" {
  name = "${local.short_prefix}-ack-lambda-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid = "",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy for Lambda execution role
resource "aws_iam_policy" "ack_lambda_exec_policy" {
  name   = "${local.short_prefix}-ack-lambda-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
       Resource = "arn:aws:logs:eu-west-2:${local.local_account_id}:log-group:/aws/lambda/${local.short_prefix}-ack-lambda:*"
      },
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.batch_prefix}-data-destinations",
          "arn:aws:s3:::${local.batch_prefix}-data-destinations/*"        
        ]
      },
      { 
        Effect = "Allow", 
        Action = [ 
                  "sqs:ReceiveMessage", 
                  "sqs:DeleteMessage", 
                  "sqs:GetQueueAttributes" 
                  ], 
        Resource = "arn:aws:sqs:eu-west-2:${local.local_account_id}:${local.short_prefix}-ack-metadata-queue.fifo" }
    ]
  })
}

resource "aws_iam_policy" "ack_s3_kms_access_policy" {
  name        = "${local.short_prefix}-ack-s3-kms-policy"
  description = "Allow Lambda to decrypt environment variables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = data.aws_kms_key.existing_s3_encryption_key.arn
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_exec_policy_attachment" {
  role       = aws_iam_role.ack_lambda_exec_role.name
  policy_arn = aws_iam_policy.ack_lambda_exec_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_kms_policy_attachment" {
  role       = aws_iam_role.ack_lambda_exec_role.name
  policy_arn = aws_iam_policy.ack_s3_kms_access_policy.arn
}
# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "ack_processor_lambda" {
  function_name   = "${local.short_prefix}-ack-lambda"
  role            = aws_iam_role.ack_lambda_exec_role.arn
  package_type    = "Image"
  image_uri       = module.ack_processor_docker_image.image_uri
  architectures   = ["x86_64"]
  timeout         = 60
  
  environment {
    variables = {
      ACK_BUCKET_NAME     = "${local.batch_prefix}-data-destinations"
    }
  }

  reserved_concurrent_executions = 20
}

resource "aws_lambda_event_source_mapping" "sqs_to_lambda"{ 
  event_source_arn = aws_sqs_queue.fifo_queue.arn 
  function_name = aws_lambda_function.ack_processor_lambda.arn 
  batch_size = 10
  enabled = true 
}