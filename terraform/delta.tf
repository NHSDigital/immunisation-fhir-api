locals {
    delta_lambda_dir    = abspath("${path.root}/../delta_backend")
    delta_files = fileset(local.delta_lambda_dir, "**")
    delta_dir_sha = sha1(join("", [for f in local.delta_files : filesha1("${local.delta_lambda_dir}/${f}")]))
    function_name = "delta"
    dlq_name = "delta-dlq"
    sns_name = "delta-sns"
}

module "delta_docker_image" {
    source = "terraform-aws-modules/lambda/aws//modules/docker-build"

    create_ecr_repo = true
    ecr_repo        = "${local.prefix}-delta-repo"
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

    platform = "linux/amd64"
    use_image_tag = false
    source_path   = local.delta_lambda_dir
    triggers = {
        dir_sha = local.delta_dir_sha
    }
}

data "aws_iam_policy_document" "delta_policy_document" {
    source_policy_documents = [
        templatefile("${local.policy_path}/dynamodb.json", {
            "dynamodb_table_name" : aws_dynamodb_table.delta-dynamodb-table.name
        } ),
        templatefile("${local.policy_path}/dynamodb_stream.json", {
            "dynamodb_table_name" : aws_dynamodb_table.events-dynamodb-table.name
        } ),
        templatefile("${local.policy_path}/aws_sqs_queue.json", {
            "aws_sqs_queue_name" : aws_sqs_queue.dlq.name
        } ),
         templatefile("${local.policy_path}/aws_sns_topic.json", {
            "aws_sns_topic_name" : aws_sns_topic.delta_sns.name
        } ),
        templatefile("${local.policy_path}/log.json", {} ),
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
  role = aws_iam_role.delta_lambda_role.arn
  package_type = "Image"
  architectures = ["x86_64"]
  image_uri    = module.delta_docker_image.image_uri
  
    
  environment {
    variables = {
      DELTA_TABLE_NAME      = aws_dynamodb_table.delta-dynamodb-table.name
      AWS_SQS_QUEUE_URL     = aws_sqs_queue.dlq.id
      SOURCE = "IEDS"
    }
  }
   
}


resource "aws_lambda_event_source_mapping" "delta_trigger" {
    event_source_arn = aws_dynamodb_table.events-dynamodb-table.stream_arn
    function_name    = aws_lambda_function.delta_sync_lambda.function_name
    starting_position = "TRIM_HORIZON"
    destination_config {
        on_failure {
          destination_arn = aws_sns_topic.delta_sns.arn
        }
    }
    maximum_retry_attempts = 2
}


resource "aws_sqs_queue" "dlq" {
    name = "${local.short_prefix}-${local.dlq_name}"
}

resource "aws_sns_topic" "delta_sns" {
    name = "${local.short_prefix}-${local.sns_name}"
}