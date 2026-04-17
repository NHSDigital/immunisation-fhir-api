locals {
  mock_pds_lambda_dir     = abspath("${path.root}/../../lambdas/mock_pds")
  mock_pds_lambda_files   = fileset(local.mock_pds_lambda_dir, "**")
  mock_pds_lambda_dir_sha = sha1(join("", [for f in local.mock_pds_lambda_files : filesha1("${local.mock_pds_lambda_dir}/${f}")]))
  mock_pds_lambda_name    = "${local.short_prefix}-mock-pds-lambda"
  mock_pds_base_url       = var.mock_pds_enabled ? "${aws_lambda_function_url.mock_pds_lambda_url[0].function_url}Patient" : ""
}

resource "aws_ecr_repository" "mock_pds_lambda_repository" {
  count = var.mock_pds_enabled ? 1 : 0

  image_scanning_configuration {
    scan_on_push = true
  }

  name         = "${local.short_prefix}-mock-pds-repo"
  force_delete = local.is_temp
}

module "mock_pds_docker_image" {
  count = var.mock_pds_enabled ? 1 : 0

  source           = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version          = "8.7.0"
  docker_file_path = "./mock_pds/Dockerfile"
  create_ecr_repo  = false
  ecr_repo         = aws_ecr_repository.mock_pds_lambda_repository[0].name
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
    dir_sha = local.mock_pds_lambda_dir_sha
  }
}

resource "aws_ecr_repository_policy" "mock_pds_lambda_ecr_image_retrieval_policy" {
  count = var.mock_pds_enabled ? 1 : 0

  repository = aws_ecr_repository.mock_pds_lambda_repository[0].name

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
            "aws:sourceArn" : "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.mock_pds_lambda_name}"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "mock_pds_lambda_exec_role" {
  count = var.mock_pds_enabled ? 1 : 0

  name = "${local.mock_pds_lambda_name}-exec-role"
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

resource "aws_iam_policy" "mock_pds_lambda_exec_policy" {
  count = var.mock_pds_enabled ? 1 : 0

  name = "${local.mock_pds_lambda_name}-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.mock_pds_lambda_name}:*"
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

resource "aws_iam_policy" "mock_pds_lambda_kms_access_policy" {
  count = var.mock_pds_enabled ? 1 : 0

  name        = "${local.mock_pds_lambda_name}-kms-policy"
  description = "Allow mock PDS Lambda to decrypt environment variables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = data.aws_kms_key.existing_lambda_encryption_key.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "mock_pds_lambda_exec_policy_attachment" {
  count = var.mock_pds_enabled ? 1 : 0

  role       = aws_iam_role.mock_pds_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mock_pds_lambda_exec_policy[0].arn
}

resource "aws_iam_role_policy_attachment" "mock_pds_lambda_kms_policy_attachment" {
  count = var.mock_pds_enabled ? 1 : 0

  role       = aws_iam_role.mock_pds_lambda_exec_role[0].name
  policy_arn = aws_iam_policy.mock_pds_lambda_kms_access_policy[0].arn
}

resource "aws_cloudwatch_log_group" "mock_pds_lambda_log_group" {
  count = var.mock_pds_enabled ? 1 : 0

  name              = "/aws/lambda/${local.mock_pds_lambda_name}"
  retention_in_days = 30
}

resource "aws_lambda_function" "mock_pds_lambda" {
  count = var.mock_pds_enabled ? 1 : 0

  function_name = local.mock_pds_lambda_name
  role          = aws_iam_role.mock_pds_lambda_exec_role[0].arn
  package_type  = "Image"
  image_uri     = module.mock_pds_docker_image[0].image_uri
  architectures = ["x86_64"]
  timeout       = 30

  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      REDIS_HOST                      = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT                      = tostring(data.aws_elasticache_cluster.existing_redis.port)
      MOCK_PDS_AVERAGE_LIMIT          = tostring(var.mock_pds_average_rate_limit)
      MOCK_PDS_AVERAGE_WINDOW_SECONDS = tostring(var.mock_pds_average_window_seconds)
      MOCK_PDS_SPIKE_LIMIT            = tostring(var.mock_pds_spike_rate_limit)
      MOCK_PDS_SPIKE_WINDOW_SECONDS   = tostring(var.mock_pds_spike_window_seconds)
      MOCK_PDS_GP_ODS_CODE            = var.mock_pds_gp_ods_code
    }
  }

  kms_key_arn = data.aws_kms_key.existing_lambda_encryption_key.arn

  depends_on = [
    aws_cloudwatch_log_group.mock_pds_lambda_log_group,
    aws_iam_policy.mock_pds_lambda_exec_policy
  ]
}

resource "aws_lambda_function_url" "mock_pds_lambda_url" {
  count = var.mock_pds_enabled ? 1 : 0

  function_name      = aws_lambda_function.mock_pds_lambda[0].function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "mock_pds_lambda_url_invoke" {
  count = var.mock_pds_enabled ? 1 : 0

  statement_id           = "AllowPublicInvokeFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.mock_pds_lambda[0].function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_cloudwatch_log_metric_filter" "mock_pds_throttle_logs" {
  count = var.mock_pds_enabled ? 1 : 0

  name           = "${local.short_prefix}-MockPdsThrottleLogs"
  pattern        = "Mock PDS rate limit exceeded"
  log_group_name = aws_cloudwatch_log_group.mock_pds_lambda_log_group[0].name

  metric_transformation {
    name      = "${local.short_prefix}-MockPdsThrottleRequests"
    namespace = "${local.short_prefix}-MockPds"
    value     = "1"
  }
}

output "mock_pds_function_url" {
  value       = var.mock_pds_enabled ? aws_lambda_function_url.mock_pds_lambda_url[0].function_url : null
  description = "Function URL for the mock PDS endpoint."
}