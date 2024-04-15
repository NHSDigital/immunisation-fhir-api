locals {
    account_id = local.environment == "prod" ? 232116723729 : 603871901111
    
}


data "aws_iam_policy_document" "dynamo_s3_policy_document" {
    source_policy_documents = [
        local.environment == "prod" ? templatefile("${local.policy_path}/dynamodb_delta.json", {
            "dynamodb_table_name" : aws_dynamodb_table.delta-dynamodb-table.name
        } ):  templatefile("${local.policy_path}/dynamodb_delta_ref.json", {
            "dynamodb_table_name" : aws_dynamodb_table.delta-dynamodb-table.name
        } ),
        templatefile("${local.policy_path}/s3_batch.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ),
    ]
}
resource "aws_iam_role" "dynamo_s3_access_role" {
 name = "${local.short_prefix}-dynamo-s3-access-role"
 assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Effect": "Allow",
     "Principal": {
       "AWS": "arn:aws:iam::${local.account_id}:root"
     },
     "Action": "sts:AssumeRole"
   }
 ]
}
EOF
}

resource "aws_iam_role_policy" "dynamo_s3_access_policy" {
    name   = "${local.short_prefix}-dynamo_s3_access-policy"
    role   = aws_iam_role.dynamo_s3_access_role.id
    policy = data.aws_iam_policy_document.dynamo_s3_policy_document.json
}
