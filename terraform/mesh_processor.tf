# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  mesh_processor_lambda_dir     = abspath("${path.root}/../mesh_processor")
  mesh_processor_lambda_files   = fileset(local.mesh_processor_lambda_dir, "**")
  mesh_processor_lambda_dir_sha = sha1(join("", [for f in local.mesh_processor_lambda_files : filesha1("${local.mesh_processor_lambda_dir}/${f}")]))
}


resource "aws_ecr_repository" "mesh_file_converter_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name = "${local.short_prefix}-mesh_processor-repo"
}

# Module for building and pushing Docker image to ECR
module "mesh_processor_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.20.2"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.mesh_file_converter_lambda_repository.name
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
  repository = aws_ecr_repository.mesh_file_converter_lambda_repository.name

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
            "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}-mesh_processor_lambda"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "mesh_processor_lambda_exec_role" {
  name = "${local.short_prefix}-mesh_processor-lambda-exec-role"
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
  name = "${local.short_prefix}-mesh_processor-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/lambda/${local.short_prefix}-mesh_processor_lambda:*"
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
          "arn:aws:s3:::${local.batch_prefix}-data-sources",
          "arn:aws:s3:::${local.batch_prefix}-data-sources/*"
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
          "arn:aws:s3:::local-immunisation-mesh",
          "arn:aws:s3:::local-immunisation-mesh/*",
          "arn:aws:s3:::local-immunisation-mesh-s3logs/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "mesh_processor_lambda_kms_access_policy" {
  name        = "${local.short_prefix}-mesh_processor-lambda-kms-policy"
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
          # "arn:aws:kms:eu-west-2:345594581768:key/9b756762-bc6f-42fb-ba56-2c0c00c15289"
        ]
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_exec_policy_attachment" {
  role       = aws_iam_role.mesh_processor_lambda_exec_role.name
  policy_arn = aws_iam_policy.mesh_processor_lambda_exec_policy.arn
}


# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_kms_policy_attachment" {
  role       = aws_iam_role.mesh_processor_lambda_exec_role.name
  policy_arn = aws_iam_policy.mesh_processor_lambda_kms_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "mesh_file_converter_lambda" {
  function_name = "${local.short_prefix}-mesh_processor_lambda"
  role          = aws_iam_role.mesh_processor_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.mesh_processor_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 360

  environment {
    variables = {
      Destination_BUCKET_NAME    = "${local.batch_prefix}-data-sources"
      MESH_FILE_PROC_LAMBDA_NAME = "imms-${local.env}-meshfileproc_lambda"
    }
  }

}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "mesh_s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mesh_file_converter_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::local-immunisation-mesh"
}

# S3 Bucket notification to trigger Lambda function
resource "aws_s3_bucket_notification" "mesh_datasources_lambda_notification" {
  bucket = "local-immunisation-mesh"

  lambda_function {
    lambda_function_arn = aws_lambda_function.mesh_file_converter_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    #filter_prefix      =""
  }
}

resource "aws_cloudwatch_log_group" "mesh_file_converter_log_group" {
  name              = "/aws/lambda/${local.short_prefix}-mesh_processor_lambda"
  retention_in_days = 30
}
