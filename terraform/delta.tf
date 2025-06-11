locals {
  delta_lambda_dir = abspath("${path.root}/../delta_backend")
  delta_files      = fileset(local.delta_lambda_dir, "**")
  delta_dir_sha    = sha1(join("", [for f in local.delta_files : filesha1("${local.delta_lambda_dir}/${f}")]))
  function_name    = "delta"
  dlq_name         = "delta-dlq"
  sns_name         = "delta-sns"
}

resource "aws_ecr_repository" "delta_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name         = "${local.prefix}-delta-lambda-repo"
  force_delete = local.is_temp
}

module "delta_docker_image" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = "7.20.2"

  create_ecr_repo = false
  ecr_repo        = "${local.prefix}-delta-lambda-repo"
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
  source_path   = local.delta_lambda_dir
  triggers = {
    dir_sha = local.delta_dir_sha
  }

}

# Define the lambdaECRImageRetreival policy
resource "aws_ecr_repository_policy" "delta_lambda_ECRImageRetreival_policy" {
  repository = aws_ecr_repository.delta_lambda_repository.name

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
            "aws:sourceArn" : "arn:aws:lambda:eu-west-2:${local.immunisation_account_id}:function:${local.short_prefix}-${local.function_name}"
          }
        }
      }
    ]
  })
}

data "aws_iam_policy_document" "delta_policy_document" {
  source_policy_documents = [
    templatefile("${local.policy_path}/dynamodb.json", {
      "dynamodb_table_name" : aws_dynamodb_table.delta-dynamodb-table.name
    }),
    templatefile("${local.policy_path}/dynamodb_stream.json", {
      "dynamodb_table_name" : aws_dynamodb_table.events-dynamodb-table.name
    }),
    templatefile("${local.policy_path}/aws_sqs_queue.json", {
      "aws_sqs_queue_name" : aws_sqs_queue.dlq.name
    }),
    templatefile("${local.policy_path}/dynamo_key_access.json", {
      "dynamo_encryption_key" : data.aws_kms_key.existing_dynamo_encryption_key.arn
    }),
    templatefile("${local.policy_path}/aws_sns_topic.json", {
      "aws_sns_topic_name" : aws_sns_topic.delta_sns.name
    }),
    templatefile("${local.policy_path}/log_kinesis.json", {
      "kinesis_stream_name" : module.splunk.firehose_stream_name
    }),
    templatefile("${local.policy_path}/log.json", {}),
  ]
}

resource "aws_iam_role" "delta_lambda_role" {
  name               = "${local.short_prefix}-${local.function_name}-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "lambda_role_policy" {
  name   = "${local.prefix}-${local.function_name}-policy"
  role   = aws_iam_role.delta_lambda_role.id
  policy = data.aws_iam_policy_document.delta_policy_document.json
}


resource "aws_lambda_function" "delta_sync_lambda" {
  function_name = "${local.short_prefix}-${local.function_name}"
  role          = aws_iam_role.delta_lambda_role.arn
  package_type  = "Image"
  architectures = ["x86_64"]
  image_uri     = module.delta_docker_image.image_uri
  timeout = 60

  environment {
    variables = {
      DELTA_TABLE_NAME     = aws_dynamodb_table.delta-dynamodb-table.name
      AWS_SQS_QUEUE_URL    = aws_sqs_queue.dlq.id
      SOURCE               = "IEDS"
      SPLUNK_FIREHOSE_NAME = module.splunk.firehose_stream_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.delta_lambda
  ]
}


resource "aws_lambda_event_source_mapping" "delta_trigger" {
  event_source_arn  = aws_dynamodb_table.events-dynamodb-table.stream_arn
  function_name     = aws_lambda_function.delta_sync_lambda.function_name
  starting_position = "TRIM_HORIZON"
  destination_config {
    on_failure {
      destination_arn = aws_sns_topic.delta_sns.arn
    }
  }
  maximum_retry_attempts = 0
}


resource "aws_sqs_queue" "dlq" {
  name = "${local.short_prefix}-${local.dlq_name}"
}

resource "aws_sns_topic" "delta_sns" {
  name = "${local.short_prefix}-${local.sns_name}"
}

resource "aws_cloudwatch_log_group" "delta_lambda" {
  name              = "/aws/lambda/${local.short_prefix}-${local.function_name}"
  retention_in_days = 30
}
