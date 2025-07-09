resource "aws_kms_key" "kinesis_stream_encryption" {
  description         = "KMS key for kinesis stream encryption"
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
    "Principal": { "AWS": "arn:aws:iam::${var.imms_account_id}:root" },
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
    "Principal": {"AWS": ["arn:aws:iam::${var.imms_account_id}:role/auto-ops"]},
    "Action": [
        "kms:Encrypt",
        "kms:GenerateDataKey*"
        ],
    "Resource": "*"
    },
    {
    "Sid": "KMS KeyUser access for Devops",
    "Effect": "Allow",
    "Principal": {"AWS": ["arn:aws:iam::${var.imms_account_id}:role/DevOps"]},
    "Action": [
        "kms:Encrypt",
        "kms:GenerateDataKey*"
        ],
    "Resource": "*"
    },
    {
      "Sid": "KMS KeyUser access for Admin",
      "Effect": "Allow",
      "Principal": { "AWS": ["arn:aws:iam::${var.imms_account_id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_PREPROD-IMMS-Admin_acce656dcacf6f4c"] },
      "Action": [
        "kms:Encrypt",
        "kms:GenerateDataKey*"
      ],
      "Resource": "*"
    }
 ]
}
POLICY
}

resource "aws_kms_alias" "kinesis_stream_encryption" {
  name          = "alias/imms-batch-kinesis-stream-encryption"
  target_key_id = aws_kms_key.kinesis_stream_encryption.key_id
}
