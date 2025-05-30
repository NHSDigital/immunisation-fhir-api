locals {
    lambda_dir    = abspath("${path.root}/../backend")
    source_path   = local.lambda_dir
    path_include  = ["**"]
    path_exclude  = ["**/__pycache__/**"]
    files_include = setunion([for f in local.path_include : fileset(local.source_path, f)]...)
    files_exclude = setunion([for f in local.path_exclude : fileset(local.source_path, f)]...)
    files         = sort(setsubtract(local.files_include, local.files_exclude))

    dir_sha = sha1(join("", [for f in local.files : filesha1("${local.source_path}/${f}")]))
}

resource "aws_ecr_repository" "operation_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name = "${local.prefix}-operation-lambda-repo"
  force_delete = local.is_temp
}

#resource "docker_image" "lambda_function_docker" {
module "docker_image" {
    source = "terraform-aws-modules/lambda/aws//modules/docker-build"
    version = "7.21.0"

    create_ecr_repo = false
    ecr_repo        = "${local.prefix}-operation-lambda-repo"
    docker_file_path = "lambda.Dockerfile"
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

    platform = "linux/amd64"
    use_image_tag = false
    source_path   = local.lambda_dir
    triggers = {
        dir_sha = local.dir_sha
    }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "operation_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.operation_lambda_repository.name

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
            "aws:sourceArn": [
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_get_status",
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_not_found",
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_search_imms",
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_get_imms",
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_delete_imms",
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_create_imms",
                  "arn:aws:lambda:eu-west-2:${local.local_account_id}:function:${local.short_prefix}_update_imms"
            ]
          }
        }
      }
  ]
  })
}
