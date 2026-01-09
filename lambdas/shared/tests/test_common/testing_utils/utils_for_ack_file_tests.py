"""Utils for the recordprocessor tests"""

from io import StringIO
from typing import Optional
from unittest.mock import patch

from boto3 import client as boto3_client
from boto3.dynamodb.types import TypeDeserializer

from test_common.testing_utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
    Firehose,
    Kinesis,
)
from test_common.testing_utils.values_for_ack_file_tests import (
    FileDetails,
    MockFileDetails,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from csv import DictReader

    from common.clients import REGION_NAME
    from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)


def convert_string_to_dict_reader(data_string: str):
    """Take a data string and convert it to a csv DictReader"""
    return DictReader(StringIO(data_string), delimiter="|")


def get_csv_file_dict_reader(s3_client, bucket_name: str, file_key: str) -> DictReader:
    """Download the file from the S3 bucket and return it as a DictReader"""
    ack_file_csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


class GenericSetUp:
    """
    Performs generic setup of mock resources:
    * If s3_client is provided, creates source, destination and firehose buckets (firehose bucket is used for testing
        only)
    * If firehose_client is provided, creates a firehose delivery stream
    * If kinesis_client is provided, creates a kinesis stream
    """

    def __init__(
        self,
        s3_client=None,
        firehose_client=None,
        kinesis_client=None,
        dynamo_db_client=None,
    ):
        if s3_client:
            for bucket_name in [
                BucketNames.SOURCE,
                BucketNames.DESTINATION,
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

        if kinesis_client:
            kinesis_client.create_stream(StreamName=Kinesis.STREAM_NAME, ShardCount=1)

        if dynamo_db_client:
            dynamo_db_client.create_table(
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
        kinesis_client=None,
        dynamo_db_client=None,
    ):
        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)

        if firehose_client:
            firehose_client.delete_delivery_stream(DeliveryStreamName=Firehose.STREAM_NAME)

        if kinesis_client:
            try:
                kinesis_client.delete_stream(StreamName=Kinesis.STREAM_NAME, EnforceConsumerDeletion=True)
            except kinesis_client.exceptions.ResourceNotFoundException:
                pass

        if dynamo_db_client:
            dynamo_db_client.delete_table(TableName=AUDIT_TABLE_NAME)


def add_entry_to_table(file_details: MockFileDetails, file_status: str) -> None:
    """Add an entry to the audit table"""
    audit_table_entry = {**file_details.audit_table_entry, "status": {"S": file_status}}
    dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=audit_table_entry)


def deserialize_dynamodb_types(dynamodb_table_entry_with_types):
    """
    Convert a dynamodb table entry with types to a table entry without types
    e.g. {'Attr1': {'S': 'val1'}, 'Attr2': {'N': 'val2'}} becomes  {'Attr1': 'val1'}
    """
    return {k: TypeDeserializer().deserialize(v) for k, v in dynamodb_table_entry_with_types.items()}


def assert_audit_table_entry(file_details: FileDetails, expected_status: str, row_count: Optional[int] = None) -> None:
    """Assert that the file details are in the audit table"""
    table_entry = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME,
        Key={AuditTableKeys.MESSAGE_ID: {"S": file_details.message_id}},
    ).get("Item")
    expected_result = {**file_details.audit_table_entry, "status": {"S": expected_status}}

    if row_count is not None:
        expected_result["record_count"] = {"N": str(row_count)}

    assert table_entry == expected_result


def create_patch(target: str):
    patcher = patch(target)
    return patcher.start()
