# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  redis_sync_lambda_dir     = abspath("${path.root}/../redis_sync")
  redis_sync_lambda_files   = fileset(local.redis_sync_lambda_dir, "**")
  redis_sync_lambda_dir_sha = sha1(join("", [for f in local.redis_sync_lambda_files : filesha1("${local.redis_sync_lambda_dir}/${f}")]))
}

resource "aws_ecr_repository" "redis_sync_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.short_prefix}-redis-sync-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "redis_sync_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.20.2"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.redis_sync_lambda_repository.name
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
  source_path   = local.redis_sync_lambda_dir
  triggers = {
    dir_sha = local.redis_sync_lambda_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "redis_sync_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.redis_sync_lambda_repository.name

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
            # "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${local.immunisation_account_id}:function:${local.short_prefix}-redis_sync_lambda"
            "aws:sourceArn" : aws_lambda_function.redis_sync_lambda.arn
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "redis_sync_lambda_exec_role" {
  name = "${local.short_prefix}-redis-sync-lambda-exec-role"
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
resource "aws_iam_policy" "redis_sync_lambda_exec_policy" {
  name = "${local.short_prefix}-redis-sync-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${local.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-redis_sync_lambda:*"
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
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          local.config_bucket_arn,
          "${local.config_bucket_arn}/*"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        "Resource" : "arn:aws:firehose:*:*:deliverystream/${module.splunk.firehose_stream_name}"
      },
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${local.immunisation_account_id}:function:imms-${local.env}-redis_sync_lambda",
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "redis_sync_lambda_kms_access_policy" {
  name        = "${local.short_prefix}-redis-sync-lambda-kms-policy"
  description = "Allow Lambda to decrypt environment variables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = data.aws_kms_key.existing_lambda_encryption_key.arn
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
        ]
      }
    ]
  })
}
#
# # IAM Role for ElastiCache.
# resource "aws_iam_role" "elasticache_exec_role" {
#   name = "${local.short_prefix}-elasticache-exec-role"
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [{
#       Effect = "Allow",
#       Sid    = "",
#       Principal = {
#         Service = "elasticache.amazonaws.com" # ElastiCache service principal
#       },
#       Action = "sts:AssumeRole"
#     }]
#   })
# }

resource "aws_iam_policy" "elasticache_permissions" {
  name = "${local.short_prefix}-elasticache-permissions"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheClusters",
          "elasticache:ListTagsForResource",
          "elasticache:AddTagsToResource",
          "elasticache:RemoveTagsFromResource"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.immunisation_account_id}:cluster/immunisation-redis-cluster"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:CreateCacheCluster",
          "elasticache:DeleteCacheCluster",
          "elasticache:ModifyCacheCluster"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.immunisation_account_id}:cluster/immunisation-redis-cluster"
        Condition = {
          "StringEquals" : {
            "aws:RequestedRegion" : var.aws_region
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheSubnetGroups"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.immunisation_account_id}:subnet-group/immunisation-redis-subnet-group"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:CreateCacheSubnetGroup",
          "elasticache:DeleteCacheSubnetGroup",
          "elasticache:ModifyCacheSubnetGroup"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.immunisation_account_id}:subnet-group/immunisation-redis-subnet-group"
        Condition = {
          "StringEquals" : {
            "aws:RequestedRegion" : var.aws_region
          }
        }
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "redis_sync_lambda_exec_policy_attachment" {
  role       = aws_iam_role.redis_sync_lambda_exec_role.name
  policy_arn = aws_iam_policy.redis_sync_lambda_exec_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "redis_sync_lambda_kms_policy_attachment" {
  role       = aws_iam_role.redis_sync_lambda_exec_role.name
  policy_arn = aws_iam_policy.redis_sync_lambda_kms_access_policy.arn
}

# Attach the policy to the ElastiCache role
resource "aws_iam_role_policy_attachment" "elasticache_policy_attachment" {
  # role       = aws_iam_role.elasticache_exec_role.name
  role       = aws_iam_role.redis_sync_lambda_exec_role.name
  policy_arn = aws_iam_policy.elasticache_permissions.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "redis_sync_lambda" {
  function_name = "${local.short_prefix}-redis_sync_lambda"
  role          = aws_iam_role.redis_sync_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.redis_sync_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 360

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      CONFIG_BUCKET_NAME          = local.config_bucket_name
      REDIS_HOST                  = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT                  = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
      REDIS_SYNC_PROC_LAMBDA_NAME = "imms-${local.env}-redis_sync_lambda"
      # SPLUNK_FIREHOSE_NAME        = module.splunk.firehose_stream_name
    }
  }
  kms_key_arn = data.aws_kms_key.existing_lambda_encryption_key.arn

  depends_on = [
    aws_cloudwatch_log_group.redis_sync_log_group,
    aws_iam_policy.redis_sync_lambda_exec_policy
  ]
}

resource "aws_cloudwatch_log_group" "redis_sync_log_group" {
  name              = "/aws/lambda/${local.short_prefix}-redis_sync_lambda"
  retention_in_days = 30
}


# S3 Bucket notification to trigger Lambda function for config bucket
resource "aws_s3_bucket_notification" "config_lambda_notification" {
  # For now, only create a trigger in internal-dev and prod as those are the envs with a config bucket
  count = local.create_config_bucket ? 1 : 0

  bucket = aws_s3_bucket.batch_config_bucket[0].bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.redis_sync_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}

# Permission for the new S3 bucket to invoke the Lambda function
resource "aws_lambda_permission" "new_s3_invoke_permission" {
  count = local.create_config_bucket ? 1 : 0

  statement_id  = "AllowExecutionFromNewS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redis_sync_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = local.config_bucket_arn
}
