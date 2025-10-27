# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  filename_lambda_dir     = abspath("${path.root}/../filenameprocessor")
  filename_lambda_files   = fileset(local.filename_lambda_dir, "**")
  filename_lambda_dir_sha = sha1(join("", [for f in local.filename_lambda_files : filesha1("${local.filename_lambda_dir}/${f}")]))
}


resource "aws_ecr_repository" "file_name_processor_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.short_prefix}-filenameproc-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "file_processor_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "8.1.0"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.file_name_processor_lambda_repository.name
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
  source_path   = local.filename_lambda_dir
  triggers = {
    dir_sha = local.filename_lambda_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "filenameprocessor_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.file_name_processor_lambda_repository.name

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
            "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${var.immunisation_account_id}:function:${local.short_prefix}-filenameproc_lambda"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "filenameprocessor_lambda_exec_role" {
  name = "${local.short_prefix}-filenameproc-lambda-exec-role"
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
resource "aws_iam_policy" "filenameprocessor_lambda_exec_policy" {
  name = "${local.short_prefix}-filenameproc-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-filenameproc_lambda:*"
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
      }
    ]
  })
}

# Policy for Lambda to interact with SQS
resource "aws_iam_policy" "filenameprocessor_lambda_sqs_policy" {
  name = "${local.short_prefix}-filenameproc-lambda-sqs-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "sqs:SendMessage"
      ],
      Resource = aws_sqs_queue.batch_file_created.arn
    }]
  })
}

resource "aws_iam_policy" "filenameprocessor_lambda_kms_access_policy" {
  name        = "${local.short_prefix}-filenameproc-lambda-kms-policy"
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

resource "aws_iam_policy" "filenameprocessor_dynamo_access_policy" {
  name        = "${local.short_prefix}-filenameproc-auditdb-policy"
  description = "Policy to allow access to DynamoDB audit table"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Effect = "Allow"
        Resource = [
          aws_dynamodb_table.audit-table.arn,
          "${aws_dynamodb_table.audit-table.arn}/index/*",
        ]
      }
    ]
  })
}


# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "filenameprocessor_lambda_exec_policy_attachment" {
  role       = aws_iam_role.filenameprocessor_lambda_exec_role.name
  policy_arn = aws_iam_policy.filenameprocessor_lambda_exec_policy.arn
}

# Attach the SQS policy to the Lambda role
resource "aws_iam_role_policy_attachment" "filenameprocessor_lambda_sqs_policy_attachment" {
  role       = aws_iam_role.filenameprocessor_lambda_exec_role.name
  policy_arn = aws_iam_policy.filenameprocessor_lambda_sqs_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "filenameprocessor_lambda_kms_policy_attachment" {
  role       = aws_iam_role.filenameprocessor_lambda_exec_role.name
  policy_arn = aws_iam_policy.filenameprocessor_lambda_kms_access_policy.arn
}

# Attach the dynamo db policy to the Lambda role
resource "aws_iam_role_policy_attachment" "filenameprocessor_lambda_dynamo_access_attachment" {
  role       = aws_iam_role.filenameprocessor_lambda_exec_role.name
  policy_arn = aws_iam_policy.filenameprocessor_dynamo_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "file_processor_lambda" {
  function_name = "${local.short_prefix}-filenameproc_lambda"
  role          = aws_iam_role.filenameprocessor_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.file_processor_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 360

  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      SOURCE_BUCKET_NAME         = aws_s3_bucket.batch_data_source_bucket.bucket
      ACK_BUCKET_NAME            = aws_s3_bucket.batch_data_destination_bucket.bucket
      QUEUE_URL                  = aws_sqs_queue.batch_file_created.url
      REDIS_HOST                 = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT                 = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
      SPLUNK_FIREHOSE_NAME       = module.splunk.firehose_stream_name
      AUDIT_TABLE_NAME           = aws_dynamodb_table.audit-table.name
      AUDIT_TABLE_TTL_DAYS       = 60
    }
  }
  kms_key_arn                    = data.aws_kms_key.existing_lambda_encryption_key.arn
  reserved_concurrent_executions = local.is_temp ? -1 : 20
  depends_on = [
    aws_cloudwatch_log_group.file_name_processor_log_group,
    aws_iam_policy.filenameprocessor_lambda_exec_policy
  ]

}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.batch_data_source_bucket.arn
}

# S3 Bucket notification to trigger Lambda function
resource "aws_s3_bucket_notification" "datasources_lambda_notification" {
  bucket = aws_s3_bucket.batch_data_source_bucket.bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}

resource "aws_cloudwatch_log_group" "file_name_processor_log_group" {
  name              = "/aws/lambda/${local.short_prefix}-filenameproc_lambda"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_metric_filter" "file_name_processor_error_logs" {
  count          = var.batch_error_notifications_enabled ? 1 : 0

  name           = "${local.short_prefix}-FilenameProcessorErrorLogsFilter"
  pattern        = "%\\[ERROR\\]%"
  log_group_name = aws_cloudwatch_log_group.file_name_processor_log_group.name

  metric_transformation {
    name      = "${local.short_prefix}-FilenameProcessorErrorLogs"
    namespace = "${local.short_prefix}-FilenameProcessorLambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "file_name_processor_error_alarm" {
  count               = var.batch_error_notifications_enabled ? 1 : 0

  alarm_name          = "${local.short_prefix}-file-name-processor-lambda-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.short_prefix}-FilenameProcessorErrorLogs"
  namespace           = "${local.short_prefix}-FilenameProcessorLambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in the file name processor Lambda function"
  alarm_actions       = [data.aws_sns_topic.batch_processor_errors.arn]
  treat_missing_data  = "notBreaching"
}
