locals {
    // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.environment)) > 0
    account_id = local.environment == "prod" ? 232116723729 : 603871901111
    local_account_id = local.environment == "prod" ? 790083933819 : 790083933819
}

 resource "aws_kms_key" "shared_key" {
    description = "KMS key for S3 batch bucket"
    enable_key_rotation = true  
    policy = <<POLICY
{
 "Version": "2012-10-17",
 "Id": "key-default-1",
 "Statement": [
    {
    "Sid": "Allow administration of the key",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::${local.local_account_id}:root" },
    "Action": [
        "kms:Create*",
        "kms:Describe*",
        "kms:Enable*",
        "kms:List*",
        "kms:Put*",
        "kms:Update*",
        "kms:Revoke*",
        "kms:Disable*",
        "kms:Get*",
        "kms:Delete*",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion",
        "kms:GenerateDataKey*",
        "kms:Decrypt"
        ],
        "Resource": "*"
    },
   {
     "Sid": "AllowAccountA",
     "Effect": "Allow",
     "Principal": {
       "AWS": "arn:aws:iam::${local.account_id}:root"
     },
     "Action": [
       "kms:Encrypt",
       "kms:Decrypt",
       "kms:GenerateDataKey*"
     ],
     "Resource": "*"
   }
 ]
}
POLICY
}

resource "aws_kms_alias" "shared_key" {
  name          = "alias/${local.prefix}-shared-key"
  target_key_id = aws_kms_key.shared_key.key_id
}

resource "aws_s3_bucket" "batch_data_source_bucket" {
    bucket        = "${local.prefix}-batch-data-source"
    force_destroy = local.is_temp
}

data "aws_iam_policy_document" "batch_data_source_bucket_policy" {
    source_policy_documents = [
        local.environment == "prod" ? templatefile("${local.policy_path}/s3_batch_policy_prod.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ):  templatefile("${local.policy_path}/s3_batch_policy.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ),
    ]
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
   bucket = aws_s3_bucket.batch_data_source_bucket.id
   policy = data.aws_iam_policy_document.batch_data_source_bucket_policy.json
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_encryption" {
  bucket = aws_s3_bucket.batch_data_source_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.shared_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_object" "covid_19_poc_folder_object" { 
	bucket = aws_s3_bucket.batch_data_source_bucket.id 
	key = "COVID19_POC/" 
	content_type = "application/x-directory" 
}

resource "aws_s3_object" "covid_19_folder_object" { 
	bucket = aws_s3_bucket.batch_data_source_bucket.id 
	key = "COVID19/" 
    content = ""
	content_type = "application/x-directory" 
}

resource "aws_s3_object" "flu_poc_folder_object" { 
	bucket = aws_s3_bucket.batch_data_source_bucket.id 
	key = "FLU_POC/" 
    content = ""
	content_type = "application/x-directory" 
}

resource "aws_s3_object" "flu_folder_object" { 
	bucket = aws_s3_bucket.batch_data_source_bucket.id 
	key = "FLU/" 
    content = ""
	content_type = "application/x-directory" 
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
            "account_id" : data.aws_caller_identity.current.account_id
        } ),
        templatefile("${local.policy_path}/log.json", {} ),
    ]
}
resource "aws_iam_policy" "batch_processing_policy" {
    name = "${local.prefix}-batch-processing-policy"
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
                    { wildcard : "*.dat" },
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
            event_time  = "$.time",
            event_id    = "$.id"
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
        },
        {
          "name" : "EVENT_TIME",
          "value" : <event_time>
        },
        {
          "name" : "EVENT_ID",
          "value" : <event_id>
        },
        {
          "name" : "ENVIRONMENT",
          "value" : "${local.environment}"
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
