# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  shared_dir         = abspath("${path.root}/../shared")
  id_sync_lambda_dir = abspath("${path.root}/../id_sync")

  # Get files from both directories
  shared_files         = fileset(local.shared_dir, "**")
  id_sync_lambda_files = fileset(local.id_sync_lambda_dir, "**")

  # Calculate SHA for both directories
  shared_dir_sha         = sha1(join("", [for f in local.shared_files : filesha1("${local.shared_dir}/${f}")]))
  id_sync_lambda_dir_sha = sha1(join("", [for f in local.id_sync_lambda_files : filesha1("${local.id_sync_lambda_dir}/${f}")]))
  id_sync_lambda_name = "${local.short_prefix}-id_sync_lambda"
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
  source           = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version          = "8.0.1"
  docker_file_path = "./id_sync/Dockerfile"
  create_ecr_repo  = false
  ecr_repo         = aws_ecr_repository.id_sync_lambda_repository.name
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
  source_path   = abspath("${path.root}/..")
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
        Resource = "arn:aws:logs:${var.aws_region}:${var.immunisation_account_id}:log-group:/aws/lambda/${local.short_prefix}-id_sync_lambda:*"
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
        Effect = "Allow",
        Action = [
          "firehose:PutRecord",
          "firehose:PutRecordBatch"
        ],
        Resource = "arn:aws:firehose:*:*:deliverystream/${module.splunk.firehose_stream_name}"
      },
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${var.immunisation_account_id}:function:${local.id_sync_lambda_name}",
        ]
      },
      # NEW
      # NB anomaly: do we want this in "id_sync_lambda_sqs_access_policy"?
      {
        Effect = "Allow",
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = "arn:aws:sqs:eu-west-2:${var.immunisation_account_id}:${local.short_prefix}-id-sync-queue"
      },
      # NB anomaly: in redis_sync this appears in "redis_sync_lambda_kms_access_policy"
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
      },
	  {
		Effect = "Allow"
		Action = [
		  "kms:Decrypt",
		  "kms:GenerateDataKey*"
		]
		Resource = data.aws_kms_key.existing_dynamo_encryption_key.arn
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

data "aws_iam_policy_document" "id_sync_policy_document" {
  source_policy_documents = [
    templatefile("${local.policy_path}/dynamodb.json", {
      "dynamodb_table_name" : aws_dynamodb_table.events-dynamodb-table.name
    }),
    templatefile("${local.policy_path}/dynamodb_stream.json", {
      "dynamodb_table_name" : aws_dynamodb_table.events-dynamodb-table.name
    }),
    templatefile("${local.policy_path}/secret_manager.json", {
      "account_id" : data.aws_caller_identity.current.account_id,
      "pds_environment" : var.pds_environment
    }),
    templatefile("${local.policy_path}/dynamo_key_access.json", {
      "dynamo_encryption_key" : data.aws_kms_key.existing_dynamo_encryption_key.arn
    })
  ]
}

resource "aws_iam_policy" "id_sync_lambda_dynamodb_access_policy" {
  name        = "${local.short_prefix}-id-sync-lambda-dynamodb-access-policy"
  description = "Allow Lambda to access DynamoDB"
  policy      = data.aws_iam_policy_document.id_sync_policy_document.json
}

# Attach the dynamodb policy to the Lambda role
resource "aws_iam_role_policy_attachment" "id_sync_lambda_dynamodb_policy_attachment" {
  role       = aws_iam_role.id_sync_lambda_exec_role.name
  policy_arn = aws_iam_policy.id_sync_lambda_dynamodb_access_policy.arn
}

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "id_sync_lambda" {
  function_name = local.id_sync_lambda_name
  role          = aws_iam_role.id_sync_lambda_exec_role.arn
  package_type  = "Image"
  image_uri     = module.id_sync_docker_image.image_uri
  architectures = ["x86_64"]
  timeout       = 360

  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [data.aws_security_group.existing_securitygroup.id]
  }

  environment {
    variables = {
      IEDS_TABLE_NAME      = aws_dynamodb_table.events-dynamodb-table.name
      PDS_ENV              = var.pds_environment
      SPLUNK_FIREHOSE_NAME = module.splunk.firehose_stream_name
    }
  }
  kms_key_arn = data.aws_kms_key.existing_lambda_encryption_key.arn

  depends_on = [
    aws_cloudwatch_log_group.id_sync_log_group,
    aws_iam_policy.id_sync_lambda_exec_policy
  ]
}

resource "aws_cloudwatch_log_group" "id_sync_log_group" {
  name              = "/aws/lambda/${local.id_sync_lambda_name}"
  retention_in_days = 30
}

# delete config_lambda_notification / new_s3_invoke_permission - not required; duplicate

# NEW
resource "aws_lambda_event_source_mapping" "id_sync_sqs_trigger" {
  event_source_arn = "arn:aws:sqs:eu-west-2:${var.immunisation_account_id}:${local.short_prefix}-id-sync-queue"
  function_name    = aws_lambda_function.id_sync_lambda.arn # TODO

  # Optional: Configure batch size and other settings
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5

  # Optional: Configure error handling
  function_response_types = ["ReportBatchItemFailures"]
}
