"""Generic setup and teardown for filenameprocessor tests"""

from unittest.mock import patch

from tests.utils_for_tests.mock_environment_variables import (
    BucketNames,
    MOCK_ENVIRONMENT_DICT,
    Sqs,
    Firehose,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from clients import REGION_NAME
    from constants import (
        AuditTableKeys,
        AUDIT_TABLE_NAME,
        AUDIT_TABLE_QUEUE_NAME_GSI,
        AUDIT_TABLE_FILENAME_GSI,
    )


class GenericSetUp:
    """
    Performs generic setup of mock resources:
    * If s3_client is provided, creates source, destination, config and firehose buckets (firehose bucket is used for
        testing only)
    * If firehose_client is provided, creates a firehose delivery stream
    * If sqs_client is provided, creates the SQS queue
    * If dynamodb_client is provided, creates the audit table
    """

    def __init__(
        self,
        s3_client=None,
        firehose_client=None,
        sqs_client=None,
        dynamodb_client=None,
    ):

        if s3_client:
            for bucket_name in [
                BucketNames.SOURCE,
                BucketNames.DESTINATION,
                BucketNames.CONFIG,
                BucketNames.MOCK_FIREHOSE,
            ]:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": REGION_NAME},
                )

        if firehose_client:
            firehose_client.create_delivery_stream(
                DeliveryStreamName=Firehose.STREAM_NAME,
                DeliveryStreamType="DirectPut",
                S3DestinationConfiguration={
                    "RoleARN": "arn:aws:iam::123456789012:role/mock-role",
                    "BucketARN": "arn:aws:s3:::" + BucketNames.MOCK_FIREHOSE,
                    "Prefix": "firehose-backup/",
                },
            )

        if sqs_client:
            sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)

        if dynamodb_client:
            dynamodb_client.create_table(
                TableName=AUDIT_TABLE_NAME,
                KeySchema=[
                    {"AttributeName": AuditTableKeys.MESSAGE_ID, "KeyType": "HASH"}
                ],
                AttributeDefinitions=[
                    {"AttributeName": AuditTableKeys.MESSAGE_ID, "AttributeType": "S"},
                    {"AttributeName": AuditTableKeys.FILENAME, "AttributeType": "S"},
                    {"AttributeName": AuditTableKeys.QUEUE_NAME, "AttributeType": "S"},
                    {"AttributeName": AuditTableKeys.STATUS, "AttributeType": "S"},
                ],
                ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": AUDIT_TABLE_FILENAME_GSI,
                        "KeySchema": [
                            {
                                "AttributeName": AuditTableKeys.FILENAME,
                                "KeyType": "HASH",
                            }
                        ],
                        "Projection": {"ProjectionType": "KEYS_ONLY"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    },
                    {
                        "IndexName": AUDIT_TABLE_QUEUE_NAME_GSI,
                        "KeySchema": [
                            {
                                "AttributeName": AuditTableKeys.QUEUE_NAME,
                                "KeyType": "HASH",
                            },
                            {
                                "AttributeName": AuditTableKeys.STATUS,
                                "KeyType": "RANGE",
                            },
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    },
                ],
            )


class GenericTearDown:
    """Performs generic tear down of mock resources"""

    def __init__(
        self,
        s3_client=None,
        firehose_client=None,
        sqs_client=None,
        dynamodb_client=None,
    ):

        if s3_client:
            for bucket_name in [
                BucketNames.SOURCE,
                BucketNames.DESTINATION,
                BucketNames.CONFIG,
                BucketNames.MOCK_FIREHOSE,
            ]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get(
                    "Contents", []
                ):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)

        if firehose_client:
            firehose_client.delete_delivery_stream(
                DeliveryStreamName=Firehose.STREAM_NAME
            )

        if sqs_client:
            sqs_client.delete_queue(QueueUrl=Sqs.TEST_QUEUE_URL)

        if dynamodb_client:
            dynamodb_client.delete_table(TableName=AUDIT_TABLE_NAME)
