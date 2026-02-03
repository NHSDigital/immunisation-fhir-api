# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  lambda_dir     = abspath("${path.root}/../../lambdas/backend")
  lambda_files   = fileset(local.lambda_dir, "**")
  lambda_dir_sha = sha1(join("", [for f in local.lambda_files : filesha1("${local.lambda_dir}/${f}")]))
}

resource "aws_ecr_repository" "operation_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.prefix}-operation-lambda-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "8.4.0"

  create_ecr_repo  = false
  ecr_repo         = "${local.prefix}-operation-lambda-repo"
  docker_file_path = "./backend/Dockerfile"
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
  source_path   = abspath("${path.root}/../../lambdas")
  triggers = {
    dir_sha        = local.lambda_dir_sha
    shared_dir_sha = local.shared_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "operation_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.operation_lambda_repository.name

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
            "aws:sourceArn" : [
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_get_status",
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_not_found",
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_search_imms",
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_get_imms",
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_delete_imms",
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_create_imms",
              "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}_update_imms"
            ]
          }
        }
      }
    ]
  })
}
