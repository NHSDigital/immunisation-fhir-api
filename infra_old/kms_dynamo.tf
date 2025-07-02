resource "aws_kms_key" "dynamodb_encryption" {
  description         = "KMS key for DynamoDB encryption"
  key_usage           = "ENCRYPT_DECRYPT"
  enable_key_rotation = true
  policy              = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "key-default-1",
  "Statement": [
    {
      "Sid": "Allow administration of the key",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::084828561157:root" },
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
        "kms:Decrypt",
        "kms:Tag*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "KMS KeyUser access",
      "Effect": "Allow",
      "Principal": { "AWS": ["arn:aws:iam::084828561157:role/auto-ops"] },
      "Action": [
        "kms:Encrypt",
        "kms:GenerateDataKey*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "KMS KeyUser access for DevOps",
      "Effect": "Allow",
      "Principal": { "AWS": ["arn:aws:iam::084828561157:role/DevOps"] },
      "Action": [
        "kms:Encrypt",
        "kms:GenerateDataKey*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "KMS KeyUser access for Admin",
      "Effect": "Allow",
      "Principal": { "AWS": ["arn:aws:iam::084828561157:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_PREPROD-IMMS-Admin_acce656dcacf6f4c"] },
      "Action": [
        "kms:Encrypt",
        "kms:GenerateDataKey*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowAccountA",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::603871901111:root"
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

resource "aws_kms_alias" "dynamodb_encryption" {
  name          = "alias/imms-event-dynamodb-encryption"
  target_key_id = aws_kms_key.dynamodb_encryption.key_id
}
