locals {
  mns_publisher_lambda_dir     = abspath("${path.root}/../../../lambdas/mns_publisher")
  mns_publisher_lambda_files   = fileset(local.mns_publisher_lambda_dir, "**")
  mns_publisher_lambda_dir_sha = sha1(join("", [for f in local.mns_publisher_lambda_files : filesha1("${local.mns_publisher_lambda_dir}/${f}")]))
  mns_publisher_lambda_name    = "${var.short_prefix}-mns-publisher-lambda"
}

resource "aws_ecr_repository" "mns_publisher_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${var.short_prefix}-mns-publisher-repo"
  force_delete = var.is_temp
}

# Module for building and pushing Docker image to ECR
module "mns_publisher_docker_image" {
  source           = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version          = "8.5.0"
  docker_file_path = "./mns_publisher/Dockerfile"

  create_ecr_repo = false
  ecr_repo        = aws_ecr_repository.mns_publisher_lambda_repository.name
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
  source_path   = abspath("${path.root}/../../../lambdas")
  triggers = {
    dir_sha        = local.mns_publisher_lambda_dir_sha
    shared_dir_sha = var.shared_dir_sha
  }
}

resource "aws_ecr_repository_policy" "mns_publisher_lambda_ecr_image_retrieval_policy" {
  repository = aws_ecr_repository.mns_publisher_lambda_repository.name

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
            "aws:sourceArn" : "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.mns_publisher_lambda_name}"
          }
        }
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "mns_publisher_lambda_exec_role" {
  name = "${local.mns_publisher_lambda_name}-exec-role"
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
resource "aws_iam_policy" "mns_publisher_lambda_exec_policy" {
  name = "${local.mns_publisher_lambda_name}-exec-policy"
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.mns_publisher_lambda_name}:*"
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
        "Resource" : "arn:aws:firehose:*:*:deliverystream/${var.splunk_firehose_stream_name}"
      },
      {
        Effect = "Allow",
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = aws_sqs_queue.mns_outbound_events.arn
      }
    ]
  })
}

resource "aws_iam_policy" "mns_publisher_lambda_kms_access_policy" {
  name        = "${local.mns_publisher_lambda_name}-kms-policy"
  description = "Allow Lambda to decrypt environment variables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = var.dynamo_kms_encryption_key_arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.mns_outbound_events.arn
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mns_publisher_lambda_exec_policy_attachment" {
  role       = aws_iam_role.mns_publisher_lambda_exec_role.name
  policy_arn = aws_iam_policy.mns_publisher_lambda_exec_policy.arn
}

# Attach the kms policy to the Lambda role
resource "aws_iam_role_policy_attachment" "mns_publisher_lambda_kms_policy_attachment" {
  role       = aws_iam_role.mns_publisher_lambda_exec_role.name
  policy_arn = aws_iam_policy.mns_publisher_lambda_kms_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "mns_publisher_lambda" {
  function_name = local.mns_publisher_lambda_name
  role          = aws_iam_role.mns_publisher_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.mns_publisher_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 120

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      SPLUNK_FIREHOSE_NAME = var.splunk_firehose_stream_name
    }
  }

  kms_key_arn                    = var.lambda_kms_encryption_key_arn
  reserved_concurrent_executions = var.is_temp ? -1 : 20
  depends_on = [
    aws_cloudwatch_log_group.mns_publisher_lambda_log_group,
    aws_iam_policy.mns_publisher_lambda_exec_policy
  ]
}

resource "aws_cloudwatch_log_group" "mns_publisher_lambda_log_group" {
  name              = "/aws/lambda/${local.mns_publisher_lambda_name}"
  retention_in_days = 30
}

resource "aws_lambda_event_source_mapping" "mns_outbound_event_sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.mns_outbound_events.arn
  function_name    = aws_lambda_function.mns_publisher_lambda.arn
  batch_size       = 10
  enabled          = true
}

resource "aws_cloudwatch_log_metric_filter" "mns_publisher_error_logs" {
  count = var.enable_lambda_alarm ? 1 : 0

  name           = "${var.short_prefix}-MnsPublisherErrorLogsFilter"
  pattern        = "%\\[ERROR\\]%"
  log_group_name = aws_cloudwatch_log_group.mns_publisher_lambda_log_group.name

  metric_transformation {
    name      = "${var.short_prefix}-MnsPublisherErrorLogs"
    namespace = "${var.short_prefix}-MnsPublisherLambda"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "mns_publisher_error_alarm" {
  count = var.enable_lambda_alarm ? 1 : 0

  alarm_name          = "${local.mns_publisher_lambda_name}-error"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${var.short_prefix}-MnsPublisherErrorLogs"
  namespace           = "${var.short_prefix}-MnsPublisherLambda"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This sets off an alarm for any error logs found in the MNS Publisher Lambda function"
  alarm_actions       = [var.system_alarm_sns_topic_arn]
  treat_missing_data  = "notBreaching"
}
