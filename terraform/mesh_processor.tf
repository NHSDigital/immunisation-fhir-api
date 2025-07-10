# Note: This is all disabled in the preprod environment
# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  mesh_processor_lambda_dir     = abspath("${path.root}/../mesh_processor")
  mesh_processor_lambda_files   = fileset(local.mesh_processor_lambda_dir, "**")
  mesh_processor_lambda_dir_sha = sha1(join("", [for f in local.mesh_processor_lambda_files : filesha1("${local.mesh_processor_lambda_dir}/${f}")]))
}


resource "aws_ecr_repository" "mesh_file_converter_lambda_repository" {
  count = local.config_env == "int" ? 0 : 1
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.short_prefix}-mesh_processor-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "mesh_processor_docker_image" {
  count   = local.config_env == "int" ? 0 : 1
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.21.1"

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
  count      = local.config_env == "int" ? 0 : 1
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
            "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${local.immunisation_account_id}:function:${local.short_prefix}-mesh_processor_lambda"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "mesh_processor_lambda_exec_role" {
  count = local.config_env == "int" ? 0 : 1
  name  = "${local.short_prefix}-mesh_processor-lambda-exec-role"
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
  count = local.config_env == "int" ? 0 : 1
  name  = "${local.short_prefix}-mesh_processor-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${local.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-mesh_processor_lambda:*"
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
          "arn:aws:s3:::local-immunisation-mesh",
          "arn:aws:s3:::local-immunisation-mesh/*",
          "arn:aws:s3:::local-immunisation-mesh-s3logs/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "mesh_processor_lambda_kms_access_policy" {
  count       = local.config_env == "int" ? 0 : 1
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
          data.aws_kms_key.mesh_s3_encryption_key[0].arn
          # "arn:aws:kms:eu-west-2:345594581768:key/9b756762-bc6f-42fb-ba56-2c0c00c15289"
        ]
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_exec_policy_attachment" {
  count      = local.config_env == "int" ? 0 : 1
  role       = aws_iam_role.mesh_processor_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mesh_processor_lambda_exec_policy[0].arn
}


# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mesh_processor_lambda_kms_policy_attachment" {
  count      = local.config_env == "int" ? 0 : 1
  role       = aws_iam_role.mesh_processor_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mesh_processor_lambda_kms_access_policy[0].arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "mesh_file_converter_lambda" {
  count         = local.config_env == "int" ? 0 : 1
  function_name = "${local.short_prefix}-mesh_processor_lambda"
  role          = aws_iam_role.mesh_processor_lambda_exec_role[0].arn
  package_type  = "Image"
  image_uri     = module.mesh_processor_docker_image[0].image_uri
  architectures = ["x86_64"]
  timeout       = 360

  environment {
    variables = {
      Destination_BUCKET_NAME    = aws_s3_bucket.batch_data_source_bucket.bucket
      MESH_FILE_PROC_LAMBDA_NAME = "imms-${local.env}-meshfileproc_lambda"
    }
  }

}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "mesh_s3_invoke_permission" {
  count         = local.config_env == "int" ? 0 : 1
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mesh_file_converter_lambda[0].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::local-immunisation-mesh"
}

# TODO - This is scoped to the bucket, so is overwritten by each deployment
# That might be intentional in prod, to switch between blue and green, but surely isn't in non-prod
# S3 Bucket notification to trigger Lambda function
resource "aws_s3_bucket_notification" "mesh_datasources_lambda_notification" {
  # TODO - what is this bucket and why isn't it managed by Terraform?
  count  = local.config_env == "int" ? 0 : 1
  bucket = "local-immunisation-mesh"

  lambda_function {
    lambda_function_arn = aws_lambda_function.mesh_file_converter_lambda[0].arn
    events              = ["s3:ObjectCreated:*"]
    #filter_prefix      =""
  }
}

resource "aws_cloudwatch_log_group" "mesh_file_converter_log_group" {
  count             = local.config_env == "int" ? 0 : 1
  name              = "/aws/lambda/${local.short_prefix}-mesh_processor_lambda"
  retention_in_days = 30
}
