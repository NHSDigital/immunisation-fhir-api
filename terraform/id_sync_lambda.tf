# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  lambdas_dir            = abspath("${path.root}/../lambdas")
  shared_dir             = abspath("${path.root}/../lambdas/shared")
  id_sync_lambda_dir     = abspath("${path.root}/../lambdas/id_sync")

  # Get files from both directories
  shared_files           = fileset(local.shared_dir, "**")
  id_sync_lambda_files   = fileset(local.id_sync_lambda_dir, "**")

  # Calculate SHA for both directories
  shared_dir_sha         = sha1(join("", [for f in local.shared_files : filesha1("${local.shared_dir}/${f}")]))
  id_sync_lambda_dir_sha = sha1(join("", [for f in local.id_sync_lambda_files : filesha1("${local.id_sync_lambda_dir}/${f}")]))

  # Combined SHA to trigger rebuild when either directory changes
  combined_sha           = sha1("${local.shared_dir_sha}${local.id_sync_lambda_dir_sha}")
}

output "debug_build_paths" {
  value = {
    lambdas_dir            = local.lambdas_dir
    shared_dir             = local.shared_dir
    id_sync_lambda_dir     = local.id_sync_lambda_dir
    shared_files_count     = length(local.shared_files)
    id_sync_files_count    = length(local.id_sync_lambda_files)
    combined_sha           = local.combined_sha
    dockerfile_exists      = fileexists("${local.id_sync_lambda_dir}/Dockerfile")
    shared_common_exists   = fileexists("${local.shared_dir}/src/common/__init__.py")
  }
}

# Debug: List some files from each directory
output "debug_file_listing" {
  value = {
    shared_files_sample    = slice(local.shared_files, 0, min(5, length(local.shared_files)))
  }
}

resource "null_resource" "debug_build_context" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "SAW === HOST SYSTEM PATHS ==="
      echo "Terraform execution directory: $(pwd)"
      echo "Host build context: ${local.lambdas_dir}"
      echo "Host Dockerfile location: ${local.id_sync_lambda_dir}/Dockerfile"
      echo ""
      echo "Docker build command that will be executed:"
      echo "docker build -f id_sync/Dockerfile ${local.lambdas_dir}"
      echo ""
      echo "=== HOST BUILD CONTEXT CONTENTS ==="
      echo "What Docker can see from host:"
      ls -la "${local.lambdas_dir}/"
    EOT
  }
}

# Reference the existing SQS queue
data "aws_sqs_queue" "existing_sqs_queue" {
  name = "id_sync_test_queue"
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
  source_path   = local.lambdas_dir    # parent lambdas directory
  docker_file_path = "id_sync/Dockerfile"  # Add this line
  triggers = {
    dir_sha = local.combined_sha       # Changed to combined SHA
  }
}

# Add a local provisioner to debug build context
resource "null_resource" "debug_build_context2" {
  triggers = {
    dir_sha = local.combined_sha
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "SAW === BUILD CONTEXT DEBUG ==="
      echo "Build context: ${local.lambdas_dir}"
      echo "Dockerfile location: ${local.id_sync_lambda_dir}/Dockerfile"
      echo ""
      echo "Checking Dockerfile exists:"
      ls -la "${local.id_sync_lambda_dir}/Dockerfile" || echo "Dockerfile NOT FOUND!"
      echo ""
      echo "Checking shared directory structure:"
      ls -la "${local.shared_dir}/src/common/" || echo "Shared common directory NOT FOUND!"
      echo ""
      echo "Files in build context (lambdas dir):"
      ls -la "${local.lambdas_dir}/"
      echo ""
      echo "Shared files structure:"
      find "${local.shared_dir}" -type f -name "*.py" | head -10
      echo ""
      echo "ID Sync files structure:"
      find "${local.id_sync_lambda_dir}" -type f -name "*.py" | head -10
    EOT
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
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = aws_ecr_repository.id_sync_lambda_repository.arn
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
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = data.aws_sqs_queue.existing_sqs_queue.arn
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

  environment {
    variables = {
      ID_SYNC_PROC_LAMBDA_NAME = "imms-${local.env}-id_sync_lambda"
      SPLUNK_FIREHOSE_NAME        = module.splunk.firehose_stream_name
      PDS_ENV                     = local.environment == "prod" ? "prod" : local.environment == "ref" ? "ref" : "int"
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

# SQS Event Source Mapping for Lambda
resource "aws_lambda_event_source_mapping" "id_sync_sqs_trigger" {
  event_source_arn = data.aws_sqs_queue.existing_sqs_queue.arn
  function_name    = aws_lambda_function.id_sync_lambda.arn

  # Optional: Configure batch size and other settings
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5

  # Optional: Configure error handling
  function_response_types = ["ReportBatchItemFailures"]
}
