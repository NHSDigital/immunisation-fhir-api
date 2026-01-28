# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  batch_processor_filter_lambda_dir     = abspath("${path.root}/../../lambdas/batch_processor_filter")
  batch_processor_filter_lambda_files   = fileset(local.batch_processor_filter_lambda_dir, "**")
  batch_processor_filter_lambda_dir_sha = sha1(join("", [for f in local.batch_processor_filter_lambda_files : filesha1("${local.batch_processor_filter_lambda_dir}/${f}")]))
}

resource "aws_ecr_repository" "batch_processor_filter_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.short_prefix}-batch-processor-filter-repo"
  force_delete = local.is_temp
}

# Module for building and pushing Docker image to ECR
module "batch_processor_filter_docker_image" {
  source           = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version          = "8.4.0"
  docker_file_path = "./batch_processor_filter/Dockerfile"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.batch_processor_filter_lambda_repository.name
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
  use_image_tag = true
  keep_remotely = true
  source_path   = abspath("${path.root}/../../lambdas")
  triggers = {
    dir_sha        = local.batch_processor_filter_lambda_dir_sha
    shared_dir_sha = local.shared_dir_sha
  }
}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "batch_processor_filter_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.batch_processor_filter_lambda_repository.name

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
            "aws:sourceArn" : "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.short_prefix}-batch-processor-filter-lambda"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "batch_processor_filter_lambda_exec_role" {
  name = "${local.short_prefix}-batch-processor-filter-lambda-exec-role"
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
resource "aws_iam_policy" "batch_processor_filter_lambda_exec_policy" {
  name = "${local.short_prefix}-batch-processor-filter-lambda-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-batch-processor-filter-lambda:*"
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
        "Effect" : "Allow",
        "Action" : [
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        "Resource" : "arn:aws:firehose:*:*:deliverystream/${module.splunk.firehose_stream_name}"
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
      }
    ]
  })
}

# Policy for Lambda to interact with SQS
resource "aws_iam_policy" "batch_processor_filter_lambda_sqs_policy" {
  name = "${local.short_prefix}-batch-processor-filter-lambda-sqs-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "sqs:SendMessage"
        ],
        Resource = aws_sqs_queue.supplier_fifo_queue.arn
      },
      {
        Effect = "Allow",
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = aws_sqs_queue.batch_file_created.arn
      }
    ]
  })
}

resource "aws_iam_policy" "batch_processor_filter_lambda_kms_access_policy" {
  name        = "${local.short_prefix}-batch-processor-filter-lambda-kms-policy"
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

resource "aws_iam_policy" "batch_processor_filter_dynamo_access_policy" {
  name        = "${local.short_prefix}-batch-processor-filter-auditdb-policy"
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
resource "aws_iam_role_policy_attachment" "batch_processor_filter_lambda_exec_policy_attachment" {
  role       = aws_iam_role.batch_processor_filter_lambda_exec_role.name
  policy_arn = aws_iam_policy.batch_processor_filter_lambda_exec_policy.arn
}

# Attach the SQS policy to the Lambda role
resource "aws_iam_role_policy_attachment" "batch_processor_filter_lambda_sqs_policy_attachment" {
  role       = aws_iam_role.batch_processor_filter_lambda_exec_role.name
  policy_arn = aws_iam_policy.batch_processor_filter_lambda_sqs_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "batch_processor_filter_lambda_kms_policy_attachment" {
  role       = aws_iam_role.batch_processor_filter_lambda_exec_role.name
  policy_arn = aws_iam_policy.batch_processor_filter_lambda_kms_access_policy.arn
}

# Attach the dynamo db policy to the Lambda role
resource "aws_iam_role_policy_attachment" "batch_processor_filter_lambda_dynamo_access_attachment" {
  role       = aws_iam_role.batch_processor_filter_lambda_exec_role.name
  policy_arn = aws_iam_policy.batch_processor_filter_dynamo_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "batch_processor_filter_lambda" {
  function_name = "${local.short_prefix}-batch-processor-filter-lambda"
  role          = aws_iam_role.batch_processor_filter_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.batch_processor_filter_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 60

  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      SOURCE_BUCKET_NAME   = aws_s3_bucket.batch_data_source_bucket.bucket
      ACK_BUCKET_NAME      = aws_s3_bucket.batch_data_destination_bucket.bucket
      QUEUE_URL            = aws_sqs_queue.supplier_fifo_queue.url
      SPLUNK_FIREHOSE_NAME = module.splunk.firehose_stream_name
      AUDIT_TABLE_NAME     = aws_dynamodb_table.audit-table.name
      FILE_NAME_GSI        = "filename_index"
      QUEUE_NAME_GSI       = "queue_name_index"
    }
  }
  kms_key_arn                    = data.aws_kms_key.existing_lambda_encryption_key.arn
  reserved_concurrent_executions = local.is_temp ? -1 : 20
  depends_on = [
    aws_cloudwatch_log_group.batch_processor_filter_lambda_log_group,
    aws_iam_policy.batch_processor_filter_lambda_exec_policy
  ]
}

resource "aws_cloudwatch_log_group" "batch_processor_filter_lambda_log_group" {
  name              = "/aws/lambda/${local.short_prefix}-batch-processor-filter-lambda"
  retention_in_days = 30
}

resource "aws_lambda_event_source_mapping" "batch_file_created_sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.batch_file_created.arn
  function_name    = aws_lambda_function.batch_processor_filter_lambda.arn
  batch_size       = 1
  enabled          = true
}

resource "aws_cloudwatch_log_metric_filter" "batch_processor_filter_error_logs" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  name = "${local.short_prefix}-BatchProcessorFilterErrorLogsFilter"
  # Ignore errors with the below exception type. This is an expected error which returns items to the queue
  pattern        = "\"[ERROR]\" -EventAlreadyProcessingForSupplierAndVaccTypeError"
  log_group_name = aws_cloudwatch_log_group.batch_processor_filter_lambda_log_group.name

  metric_transformation {
    name      = "${local.short_prefix}-BatchProcessorFilterErrorLogs"
    namespace = "${local.short_prefix}-BatchProcessorFilterLambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "batch_processor_filter_error_alarm" {
  count = var.error_alarm_notifications_enabled ? 1 : 0

  alarm_name          = "${local.short_prefix}-batch-processor-filter-lambda-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.short_prefix}-BatchProcessorFilterErrorLogs"
  namespace           = "${local.short_prefix}-BatchProcessorFilterLambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in the batch processor filter Lambda function"
  alarm_actions       = [data.aws_sns_topic.imms_system_alert_errors.arn]
  treat_missing_data  = "notBreaching"
}
