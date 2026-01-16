"""Utils functions for filenameprocessor tests"""

from unittest.mock import patch

from boto3 import client as boto3_client

from utils_for_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
    Firehose,
    Sqs,
)
from utils_for_tests.values_for_tests import FileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys
    from common.models.constants import RedisHashKeys
    from constants import ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY

MOCK_ODS_CODE_TO_SUPPLIER = {"YGM41": "EMIS", "X8E5B": "RAVS"}

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)


def assert_audit_table_entry(file_details: FileDetails, expected_status: str) -> None:
    """Assert that the file details are in the audit table"""
    table_entry = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME,
        Key={AuditTableKeys.MESSAGE_ID: {"S": file_details.message_id}},
    ).get("Item")
    assert table_entry == {
        **file_details.audit_table_entry,
        "status": {"S": expected_status},
    }


def create_mock_hget(
    mock_ods_code_to_supplier: dict[str, str],
    mock_supplier_permissions: dict[str, str],
):
    def mock_hget(key, field):
        if key == ODS_CODE_TO_SUPPLIER_SYSTEM_HASH_KEY:
            return mock_ods_code_to_supplier.get(field)
        if key == RedisHashKeys.SUPPLIER_PERMISSIONS_HASH_KEY:
            return mock_supplier_permissions.get(field)
        return None

    return mock_hget


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
                BucketNames.DPS_DESTINATION,
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
                KeySchema=[{"AttributeName": AuditTableKeys.MESSAGE_ID, "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": AuditTableKeys.MESSAGE_ID, "AttributeType": "S"}],
                ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
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
                BucketNames.DPS_DESTINATION,
                BucketNames.CONFIG,
                BucketNames.MOCK_FIREHOSE,
            ]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)

        if firehose_client:
            firehose_client.delete_delivery_stream(DeliveryStreamName=Firehose.STREAM_NAME)

        if sqs_client:
            sqs_client.delete_queue(QueueUrl=Sqs.TEST_QUEUE_URL)

        if dynamodb_client:
            dynamodb_client.delete_table(TableName=AUDIT_TABLE_NAME)
