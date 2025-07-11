# Only create MESH processor resources if MESH is configured for this environment
locals {
  create_mesh_processor = var.mesh_mailbox_id != null 
}

# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  mesh_processor_lambda_dir     = abspath("${path.root}/../mesh_processor")
  mesh_processor_lambda_files   = fileset(local.mesh_processor_lambda_dir, "**")
  mesh_processor_lambda_dir_sha = sha1(join("", [for f in local.mesh_processor_lambda_files : filesha1("${local.mesh_processor_lambda_dir}/${f}")]))
  mesh_s3_bucket_name          = local.create_mesh_processor ? module.mesh[0].mesh_bucket_name : null
  mesh_s3_logs_bucket_name      = local.create_mesh_processor ? module.mesh[0].mesh_logs_bucket_name : null
  mesh_processor_name           = "imms-${var.environment}-mesh-processor"
  mesh_processor_lambda_name    = "${local.mesh_processor_name}-lambda"
}

resource "aws_ecr_repository" "mesh_file_converter_lambda_repository" {
  count = local.create_mesh_processor ? 1 : 0
  
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.mesh_processor_name}-repo"
  force_delete = false
}

# Module for building and pushing Docker image to ECR
module "mesh_processor_docker_image" {
  count   = local.create_mesh_processor ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "8.0.1"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.mesh_file_converter_lambda_repository[0].name
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
  source_path   = local.mesh_processor_lambda_dir
  triggers = {
    dir_sha = local.mesh_processor_lambda_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "mesh_processor_lambda_ECRImageRetreival_policy" {
  count      = local.create_mesh_processor ? 1 : 0
  repository = aws_ecr_repository.mesh_file_converter_lambda_repository[0].name

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
            "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${var.imms_account_id}:function:${local.mesh_processor_lambda_name}"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "mesh_processor_lambda_exec_role" {
  count = local.create_mesh_processor ? 1 : 0
  name  = "${local.mesh_processor_lambda_name}-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid    = "",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy for Lambda execution role
resource "aws_iam_policy" "mesh_processor_lambda_exec_policy" {
  count = local.create_mesh_processor ? 1 : 0
  name  = "imms-${var.environment}-mesh_processor-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.imms_account_id}:log-group:/aws/lambda/${local.mesh_processor_lambda_name}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:CopyObject"
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
          "s3:ListBucket",
          "s3:PutObject",
          "s3:CopyObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${local.mesh_s3_bucket_name}",
          "arn:aws:s3:::${local.mesh_s3_bucket_name}/*",
          "arn:aws:s3:::${local.mesh_s3_logs_bucket_name}/*",
          "arn:aws:s3:::local-immunisation-mesh",
          "arn:aws:s3:::local-immunisation-mesh/*",
          "arn:aws:s3:::local-immunisation-mesh-s3logs/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "mesh_processor_lambda_kms_access_policy" {
  count       = local.create_mesh_processor ? 1 : 0
  name        = "${aws_lambda_function.mesh_file_converter_lambda[0].function_name}-kms-policy"
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
        Resource = [
          data.aws_kms_key.mesh_s3_encryption_key.arn
        ]
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_exec_policy_attachment" {
  count      = local.create_mesh_processor ? 1 : 0
  role       = aws_iam_role.mesh_processor_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mesh_processor_lambda_exec_policy[0].arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_kms_policy_attachment" {
  count      = local.create_mesh_processor ? 1 : 0
  role       = aws_iam_role.mesh_processor_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mesh_processor_lambda_kms_access_policy[0].arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "mesh_file_converter_lambda" {
  count         = local.create_mesh_processor ? 1 : 0
  function_name = "${local.mesh_processor_name}_lambda"
  role          = aws_iam_role.mesh_processor_lambda_exec_role[0].arn
  package_type  = "Image"
  image_uri     = module.mesh_processor_docker_image[0].image_uri
  architectures = ["x86_64"]
  timeout       = 360

  environment {
    variables = {
      Destination_BUCKET_NAME    = aws_s3_bucket.batch_data_source_bucket.bucket
      MESH_FILE_PROC_LAMBDA_NAME = "${local.mesh_processor_lambda_name}"
    }
  }
}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "mesh_s3_invoke_permission" {
  count         = local.create_mesh_processor ? 1 : 0
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mesh_file_converter_lambda[0].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${local.mesh_s3_bucket_name}"
}

# S3 Bucket notification to trigger Lambda function
resource "aws_s3_bucket_notification" "mesh_datasources_lambda_notification" {
  count  = local.create_mesh_processor ? 1 : 0
  bucket = local.mesh_s3_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.mesh_file_converter_lambda[0].arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.mesh_s3_invoke_permission]
}

resource "aws_cloudwatch_log_group" "mesh_file_converter_log_group" {
  count             = local.create_mesh_processor ? 1 : 0
  name              = "/aws/lambda/${aws_lambda_function.mesh_file_converter_lambda[0].function_name}"
  retention_in_days = 30
}