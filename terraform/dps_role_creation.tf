data "aws_iam_policy_document" "dynamo_s3_policy_document" {

    # note: The policy "dynamodb:BatchGetItem" may be added manually in non-prod
    # to allow DPS access. It is not to added to prod or code as it is for testing only.
    source_policy_documents = [
        local.environment == "prod" ? templatefile("${local.policy_path}/dynamodb_delta_prod.json", {
            "dynamodb_table_name" : data.aws_dynamodb_table.delta-dynamodb-table.name
        } ):  templatefile("${local.policy_path}/dynamodb_delta.json", {
            "dynamodb_table_name" : data.aws_dynamodb_table.delta-dynamodb-table.name
        } )        
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