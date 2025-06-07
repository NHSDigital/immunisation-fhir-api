# Define the directory containing source code and calculate its SHA-256 hash for triggering redeployments
locals {
  redis_sync_dir     = abspath("${path.root}/../redis_sync")
  redis_sync_files   = fileset(local.redis_sync_dir, "**")
  redis_sync_dir_sha = sha1(join("", [for f in local.redis_sync_files : filesha1("${local.redis_sync_dir}/${f}")]))
}

output "redis_sync_dir" {
  value = "redis_sync_dir: ${local.redis_sync_dir}"
}

output "redis_sync_files" {
  value = "redis_sync_files: ${join(", ", local.redis_sync_files)}"
}

data "archive_file" "redis_sync_lambda_zip" {
  type        = "zip"
  source_dir  = local.redis_sync_dir
  output_path = "${path.module}/build/redis_sync_lambda.zip"
}

resource "aws_lambda_function" "redis_sync_lambda" {
  function_name = "${local.short_prefix}-redis-sync-lambda"
  role          = aws_iam_role.redis_sync_lambda_exec_role.arn
  handler       = "redis_sync.sync_handler" # Update as appropriate
  runtime       = "python3.11"
  filename      = data.archive_file.redis_sync_lambda_zip.output_path
  source_code_hash = data.archive_file.redis_sync_lambda_zip.output_base64sha256
  architectures = ["x86_64"]
  timeout       = 360

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      CONFIG_BUCKET_NAME         = local.config_bucket_name
      REDIS_HOST                 = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT                 = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
      REDIS_SYNC_PROC_LAMBDA_NAME = "imms-${local.env}-redis_sync_lambda"
    }
  }
  kms_key_arn                    = data.aws_kms_key.existing_lambda_encryption_key.arn
  reserved_concurrent_executions = local.is_temp ? -1 : 20
  depends_on = [
    aws_cloudwatch_log_group.redis_sync_lambda_log_group,
    aws_iam_policy.redis_sync_lambda_exec_policy
  ]
}

resource "aws_lambda_version" "redis_sync_lambda_version" {
  function_name = aws_lambda_function.redis_sync_lambda.function_name
  description   = "Automatic version for redis_sync_lambda"

  # This ensures a new version is published when the code or config changes
  lifecycle {
    create_before_destroy = true
  }
}

output "redis_sync_lambda_version" {
  value = aws_lambda_version.redis_sync_lambda_version.version
  description = "The published version number of the redis_sync_lambda Lambda function"
}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "redis_sync_s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redis_sync_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::imms-${local.env}-supplier-config"
}

# S3 Bucket notification to trigger Lambda function
resource "aws_s3_bucket_notification" "redis_sync_lambda_notification" {
  bucket = "imms-${local.env}-supplier-config"

  lambda_function {
    lambda_function_arn = aws_lambda_function.redis_sync_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    # filter_prefix      = ""
    # filter_suffix      = ""
  }

  depends_on = [aws_lambda_permission.redis_sync_s3_invoke_permission]
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
          data.aws_kms_key.existing_dynamo_encryption_key.arn
        ]
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

# IAM Role for ElastiCache.
resource "aws_iam_role" "elasticache_exec_role" {
  name = "${local.short_prefix}-elasticache-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid    = "",
      Principal = {
        Service = "elasticache.amazonaws.com" # ElastiCache service principal
      },
      Action = "sts:AssumeRole"
    }]
  })
}

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

# Attach the policy to the ElastiCache role
resource "aws_iam_role_policy_attachment" "elasticache_policy_attachment" {
  role       = aws_iam_role.elasticache_exec_role.name
  policy_arn = aws_iam_policy.elasticache_permissions.arn
}

resource "aws_cloudwatch_log_group" "redis_sync_lambda_log_group" {
  name              = "/aws/lambda/${local.short_prefix}-redis_sync_lambda"
  retention_in_days = 30
}
