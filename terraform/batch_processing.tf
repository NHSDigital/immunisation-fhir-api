locals {
    // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.environment)) > 0
}

resource "aws_s3_bucket" "batch_data_source_bucket" {
    bucket        = "${local.prefix}-batch-data-source"
    force_destroy = local.is_temp
}
resource "aws_s3_bucket_notification" "source_bucket_notification" {
    bucket      = aws_s3_bucket.batch_data_source_bucket.bucket
    eventbridge = true
}

resource "aws_s3_bucket" "batch_data_destination_bucket" {
    bucket        = "${local.prefix}-batch-data-destination"
    force_destroy = local.is_temp
}

data "aws_iam_policy_document" "batch_processing_policy_document" {
    source_policy_documents = [
        templatefile("${local.policy_path}/batch_processing.json", {
            "batch_processing_source_bucket" : aws_s3_bucket.batch_data_source_bucket.bucket
            "batch_processing_destination_bucket" : aws_s3_bucket.batch_data_destination_bucket.bucket
        } ),
        templatefile("${local.policy_path}/log.json", {} ),
    ]
}
resource "aws_iam_policy" "batch_processing_policy" {
    policy = data.aws_iam_policy_document.batch_processing_policy_document.json
}

resource "aws_cloudwatch_event_rule" "source_bucket_event_rule" {
    name        = "${local.prefix}-source-bucket-event-rule"
    description = "This rule detects changes in the source bucket"
    role_arn    = ""

    event_pattern = jsonencode({
        source : ["aws.s3"],
        detail-type : ["Object Created"],
        detail : {
            bucket : {
                name : [aws_s3_bucket.batch_data_source_bucket.bucket]
            },
            object : {
                key : [
                    { wildcard : "*" },
                ]
            }
        }
    })
}


module "batch_processing" {
    source          = "./batch_processing"
    short_prefix = local.short_prefix
    vpc_id          = data.aws_vpc.default.id
    task_policy_arn = aws_iam_policy.batch_processing_policy.arn
}
resource "aws_cloudwatch_event_target" "serverlessland-s3-event-ecs-event-target" {
    target_id      = "${local.prefix}-batch-processing-ecs-target"
    rule           = aws_cloudwatch_event_rule.source_bucket_event_rule.name
    arn            = module.batch_processing.cluster_arn
    role_arn       = aws_iam_role.batch-invoke-ecs-role.arn
    # aws services only send events to the default event bus
    event_bus_name = "default"

    ecs_target {
        task_count          = 1
        task_definition_arn = module.batch_processing.batch_task_arn
        launch_type         = "FARGATE"

        network_configuration {
            subnets          = data.aws_subnets.default.ids
            assign_public_ip = true
        }
    }

    input_transformer {
        input_paths = {
            bucket_name = "$.detail.bucket.name",
            object_key  = "$.detail.object.key",
        }
        input_template = <<EOF
{
  "containerOverrides": [
    {
      "name": "${module.batch_processing.container_name}",
      "environment" : [
        {
          "name" : "DESTINATION_BUCKET_NAME",
          "value" : "${aws_s3_bucket.batch_data_destination_bucket.bucket}"
        },
        {
          "name" : "SOURCE_BUCKET_NAME",
          "value" : <bucket_name>
        },
        {
          "name" : "OBJECT_KEY",
          "value" : <object_key>
        }
      ]
    }
  ]
}
EOF
    }
}
resource "aws_iam_role" "batch-invoke-ecs-role" {
    name                = "${local.prefix}-invoke-ecs-role"
    managed_policy_arns = [aws_iam_policy.batch-invoke-ecs-policy.arn]

    assume_role_policy = jsonencode({
        Version   = "2012-10-17"
        Statement = [
            {
                Action    = "sts:AssumeRole"
                Effect    = "Allow"
                Sid       = ""
                Principal = {
                    Service = "events.amazonaws.com"
                }
            },
        ]
    })
}
resource "aws_iam_policy" "batch-invoke-ecs-policy" {
    name = "${local.prefix}-invoke-ecs-policy"

    policy = jsonencode({
        "Version" : "2012-10-17",
        "Statement" : [
            {
                "Effect" : "Allow",
                "Action" : [
                    "ecs:RunTask"
                ],
                "Resource" : [
                    "${module.batch_processing.batch_task_arn}:*",
                    module.batch_processing.batch_task_arn
                ],
                "Condition" : {
                    "ArnLike" : {
                        "ecs:cluster" : module.batch_processing.cluster_arn
                    }
                }
            },
            {
                "Effect" : "Allow",
                "Action" : "iam:PassRole",
                "Resource" : [
                    "*"
                ],
                "Condition" : {
                    "StringLike" : {
                        "iam:PassedToService" : "ecs-tasks.amazonaws.com"
                    }
                }
            }
        ]
    })
}
