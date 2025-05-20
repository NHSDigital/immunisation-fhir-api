# Define the ECS Cluster
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "${local.short_prefix}-ecs-cluster"
}

# Locals for Lambda processing paths and hash
locals {
  processing_lambda_dir     = abspath("${path.root}/../recordprocessor")
  processing_path_include   = ["**"]
  processing_path_exclude   = ["**/__pycache__/**"]
  processing_files_include  = setunion([for f in local.processing_path_include : fileset(local.processing_lambda_dir, f)]...)
  processing_files_exclude  = setunion([for f in local.processing_path_exclude : fileset(local.processing_lambda_dir, f)]...)
  processing_lambda_files   = sort(setsubtract(local.processing_files_include, local.processing_files_exclude))
  processing_lambda_dir_sha = sha1(join("", [for f in local.processing_lambda_files : filesha1("${local.processing_lambda_dir}/${f}")]))
  image_tag                 = "latest"
}

# Create ECR Repository for processing.
resource "aws_ecr_repository" "processing_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name = "${local.short_prefix}-processing-repo"
  force_delete = local.is_temp
}

# Build and Push Docker Image to ECR (Reusing the existing module)
module "processing_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.20.2"

  docker_file_path = "Dockerfile"
  create_ecr_repo  = false
  ecr_repo         = aws_ecr_repository.processing_repository.name
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
  source_path   = local.processing_lambda_dir
  triggers = {
    dir_sha = local.processing_lambda_dir_sha
  }
}

# Define the IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_exec_role" {
  name = "${local.short_prefix}-ecs-task-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution_ecr_policy" {
  role       = aws_iam_role.ecs_task_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Define the IAM Role for ECS Task Execution with Kinesis Permissions
resource "aws_iam_policy" "ecs_task_exec_policy" {
  name = "${local.short_prefix}-ecs-task-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/vendedlogs/ecs/${local.short_prefix}-processor-task:*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:CopyObject",
          "s3:DeleteObject"
        ],
        Resource = [
          aws_s3_bucket.batch_data_source_bucket.arn,
          "${aws_s3_bucket.batch_data_source_bucket.arn}/*",
          data.aws_s3_bucket.existing_destination_bucket.arn,
          "${data.aws_s3_bucket.existing_destination_bucket.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
       Resource  = [
          # TODO - is this just the table ARN?
          "arn:aws:dynamodb:${var.aws_region}:${local.local_account_id}:table/${aws_dynamodb_table.audit-table.name}",
          "arn:aws:dynamodb:${var.aws_region}:${local.local_account_id}:table/${aws_dynamodb_table.audit-table.name}/index/*",
        ]
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
          data.aws_kms_key.existing_kinesis_encryption_key.arn,
          data.aws_kms_key.existing_dynamo_encryption_key.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ],
        Resource = local.kinesis_arn
      },
      {
        Effect = "Allow",
        Action = [
          "ecr:GetAuthorizationToken"
        ],
        Resource = "arn:aws:ecr:${var.aws_region}:${local.local_account_id}:repository/${local.short_prefix}-processing-repo"
      },
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.file_processor_lambda.arn
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

resource "aws_iam_role_policy_attachment" "ecs_task_exec_policy_attachment" {
  role       = aws_iam_role.ecs_task_exec_role.name
  policy_arn = aws_iam_policy.ecs_task_exec_policy.arn
}

resource "aws_cloudwatch_log_group" "ecs_task_log_group" {
  name = "/aws/vendedlogs/ecs/${local.short_prefix}-processor-task"
  retention_in_days =  30
}

# Create the ECS Task Definition
resource "aws_ecs_task_definition" "ecs_task" {
  family                   = "${local.short_prefix}-processor-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "8192"
  memory                   = "24576"
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  task_role_arn      = aws_iam_role.ecs_task_exec_role.arn
  execution_role_arn = aws_iam_role.ecs_task_exec_role.arn

  container_definitions = jsonencode([{
    name      = "${local.short_prefix}-process-records-container"
    image     = "${aws_ecr_repository.processing_repository.repository_url}:${local.image_tag}"
    essential = true
    environment = [
      {
        name  = "SOURCE_BUCKET_NAME"
        value = aws_s3_bucket.batch_data_source_bucket.bucket
      },
      {
        name  = "ACK_BUCKET_NAME"
        value = data.aws_s3_bucket.existing_destination_bucket.bucket
      },
      {
        name  = "KINESIS_STREAM_ARN"
        value = local.kinesis_arn
      },
      {
        name  = "KINESIS_STREAM_NAME"
        value = "${local.short_prefix}-processingdata-stream"
      },
      {
        name  = "SPLUNK_FIREHOSE_NAME"
        value = module.splunk.firehose_stream_name
      },
      {
        name  = "AUDIT_TABLE_NAME"
        value = aws_dynamodb_table.audit-table.name
      },
      {
        name  = "FILE_NAME_PROC_LAMBDA_NAME"
        value =  aws_lambda_function.file_processor_lambda.function_name
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/aws/vendedlogs/ecs/${local.short_prefix}-processor-task"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
  depends_on = [aws_cloudwatch_log_group.ecs_task_log_group]
}

# IAM Role for EventBridge Pipe
resource "aws_iam_role" "fifo_pipe_role" {
  name = "${local.short_prefix}-eventbridge-pipe-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "pipes.amazonaws.com"
        }
      }
    ]
  })
}
resource "aws_iam_policy" "fifo_pipe_policy" {
  name = "${local.short_prefix}-fifo-pipe-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "pipes:CreatePipe",
          "pipes:StartPipe",
          "pipes:StopPipe",
          "pipes:DeletePipe",
          "pipes:UpdatePipe",
          "pipes:DescribePipe"
        ],
        Resource = [
          "arn:aws:pipes:${var.aws_region}:${local.local_account_id}:pipe/${local.short_prefix}-pipe",
          aws_ecs_task_definition.ecs_task.arn
        ]
      },
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "ecs:RunTask",
          "ecs:StartTask",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect = "Allow",
        Resource = [
          "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/vendedlogs/pipes/${local.short_prefix}-pipe-logs:*",
          "arn:aws:ecs:${var.aws_region}:${local.local_account_id}:task/${local.short_prefix}-ecs-cluster/*",
          "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/vendedlogs/ecs/${local.short_prefix}-processor-task:*",
          aws_sqs_queue.supplier_fifo_queue.arn,
          "arn:aws:ecs:${var.aws_region}:${local.local_account_id}:cluster/${local.short_prefix}-ecs-cluster",
          aws_ecs_task_definition.ecs_task.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "iam:PassRole"
        ],
        Resource = aws_iam_role.ecs_task_exec_role.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "fifo_pipe_policy_attachment" {
  role       = aws_iam_role.fifo_pipe_role.name
  policy_arn = aws_iam_policy.fifo_pipe_policy.arn
}


# EventBridge Pipe
resource "aws_pipes_pipe" "fifo_pipe" {
  name     = "${local.short_prefix}-pipe"
  role_arn = aws_iam_role.fifo_pipe_role.arn
  source   = aws_sqs_queue.supplier_fifo_queue.arn
  target   = aws_ecs_cluster.ecs_cluster.arn

  target_parameters {
    ecs_task_parameters {
      task_definition_arn = aws_ecs_task_definition.ecs_task.arn
      launch_type         = "FARGATE"
      network_configuration {
        aws_vpc_configuration {
          subnets          = data.aws_subnets.default.ids
          assign_public_ip = "ENABLED"
        }
      }
      overrides {
        container_override {
          cpu  = 2048
          name = "${local.short_prefix}-process-records-container"
          environment {
            name  = "EVENT_DETAILS"
            value = "$.body"
          }
          memory             = 8192
          memory_reservation = 1024
        }
      }
      task_count = 1
    }

  }
  log_configuration {
    include_execution_data = ["ALL"]
    level                  = "ERROR"
    cloudwatch_logs_log_destination {
      log_group_arn = aws_cloudwatch_log_group.pipe_log_group.arn
    }
  }
}

# Custom Log Group
resource "aws_cloudwatch_log_group" "pipe_log_group" {
  name = "/aws/vendedlogs/pipes/${local.short_prefix}-pipe-logs"
  retention_in_days = 30
}
