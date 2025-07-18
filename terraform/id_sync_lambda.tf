# Prototype of id_sync_lambda.tf

# This is a WIP.
# This is an attempt to define the terraform for the new NHS MNS id sync lambda.
# Some resources may be unnecessary.
# The ones we do require for SQS queue and its KMS key are at the bottom of the lambda execution policy.

# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  id_sync_lambda_dir     = abspath("${path.root}/../id_sync")
  id_sync_lambda_files   = fileset(local.id_sync_lambda_dir, "**")
  id_sync_lambda_dir_sha = sha1(join("", [for f in local.id_sync_lambda_files : filesha1("${local.id_sync_lambda_dir}/${f}")]))
}

resource "aws_ecr_repository" "id_sync_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.short_prefix}-id-sync-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "id_sync_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "8.0.1"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.id_sync_lambda_repository.name
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
  source_path   = local.id_sync_lambda_dir
  triggers = {
    dir_sha = local.id_sync_lambda_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "id_sync_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.id_sync_lambda_repository.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid : "LambdaECRImageRetrievalPolicy",
        Effect : "Allow",
        Principal : {
          Service : "lambda.amazonaws.com"
        },
        Action : [
          "ecr:BatchGetImage",
          "ecr:DeleteRepositoryPolicy",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:SetRepositoryPolicy"
        ],
        Condition : {
          StringLike : {
            # "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${local.immunisation_account_id}:function:${local.short_prefix}-id_sync_lambda"
            "aws:sourceArn" : aws_lambda_function.id_sync_lambda.arn
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "id_sync_lambda_exec_role" {
  name = "${local.short_prefix}-id-sync-lambda-exec-role"
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
resource "aws_iam_policy" "id_sync_lambda_exec_policy" {
  name = "${local.short_prefix}-id-sync-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${local.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-id_sync_lambda:*"
      },
      # ** TODO need to ascertain whether we need these S3 policies. possibly not. we WILL need an SQS policy though.
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
      # ** TODO: do we need these ec2 policies? I think they're to do with VPCs
      {
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Resource = "*"
      },
      # ** TODO: ditto. The bucket is imms-${local.environment}-fhir-config
      # Examine it.
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
        Effect : "Allow",
        Action : [
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        Resource : "arn:aws:firehose:*:*:deliverystream/${module.splunk.firehose_stream_name}"
      },
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${local.immunisation_account_id}:function:imms-${local.env}-id_sync_lambda",
        ]
      },
      # New: required for SQS queue and its KMS key

      # Notes: these elements are currently defined in branch VED-80-id-sync-sqs
      #     - the SQS queue in terraform/sqs_id_sync.tf
      #     - the KMS key in terraform/temp_id_sync_sqs_kms.tf; this will eventually be replaced by
      #         the version of infra/kms.tf in branch VED-80-id-sync-sqs-infra
      #     - aws_kms_key.existing_id_sync_sqs_encryption_key in terraform/variables.tf

      {
        Effect = "Allow",
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = "arn:aws:sqs:eu-west-2:${local.immunisation_account_id}:${local.short_prefix}-id-sync-queue"
      }
      {
        Effect = "Allow",
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ],
        Resource = data.aws_kms_key.existing_id_sync_sqs_encryption_key.arn
      }
    ]
  })
}

resource "aws_iam_policy" "id_sync_lambda_kms_access_policy" {
  name        = "${local.short_prefix}-id-sync-lambda-kms-policy"
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

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "id_sync_lambda_exec_policy_attachment" {
  role       = aws_iam_role.id_sync_lambda_exec_role.name
  policy_arn = aws_iam_policy.id_sync_lambda_exec_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "id_sync_lambda_kms_policy_attachment" {
  role       = aws_iam_role.id_sync_lambda_exec_role.name
  policy_arn = aws_iam_policy.id_sync_lambda_kms_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "id_sync_lambda" {
  function_name = "${local.short_prefix}-id_sync_lambda"
  role          = aws_iam_role.id_sync_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.id_sync_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 360

  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  # ** TODO: we're likely to not need any of the REDIS_ variables
  environment {
    variables = {
      CONFIG_BUCKET_NAME          = local.config_bucket_name
      REDIS_HOST                  = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT                  = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
      ID_SYNC_PROC_LAMBDA_NAME    = "imms-${local.env}-id_sync_lambda"
      SPLUNK_FIREHOSE_NAME        = module.splunk.firehose_stream_name
    }
  }
  kms_key_arn = data.aws_kms_key.existing_lambda_encryption_key.arn

  depends_on = [
    aws_cloudwatch_log_group.id_sync_log_group,
    aws_iam_policy.id_sync_lambda_exec_policy
  ]
}

resource "aws_cloudwatch_log_group" "id_sync_log_group" {
  name              = "/aws/lambda/${local.short_prefix}-id_sync_lambda"
  retention_in_days = 30
}


# S3 Bucket notification to trigger Lambda function for config bucket
resource "aws_s3_bucket_notification" "config_lambda_notification" {

  bucket = aws_s3_bucket.batch_config_bucket.bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.id_sync_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}

# Permission for the new S3 bucket to invoke the Lambda function
resource "aws_lambda_permission" "new_s3_invoke_permission" {

  statement_id  = "AllowExecutionFromNewS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.id_sync_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = local.config_bucket_arn
}
