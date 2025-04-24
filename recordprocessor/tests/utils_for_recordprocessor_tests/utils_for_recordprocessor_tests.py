"""Utils for the recordprocessor tests"""

from io import StringIO
from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    BucketNames,
    Firehose,
    Kinesis,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFileDetails,
    FileDetails,
)
from boto3.dynamodb.types import TypeDeserializer
from boto3 import client as boto3_client
from unittest.mock import patch
from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from clients import REGION_NAME
    from csv import DictReader
    from constants import AuditTableKeys, AUDIT_TABLE_NAME, FileStatus

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

    def __init__(self, s3_client=None, firehose_client=None, kinesis_client=None):

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


class GenericTearDown:
    """Performs generic tear down of mock resources"""

    def __init__(self, s3_client=None, firehose_client=None, kinesis_client=None):

        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get(
                    "Contents", []
                ):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)

        if firehose_client:
            firehose_client.delete_delivery_stream(
                DeliveryStreamName=Firehose.STREAM_NAME
            )

        if kinesis_client:
            try:
                kinesis_client.delete_stream(
                    StreamName=Kinesis.STREAM_NAME, EnforceConsumerDeletion=True
                )
            except kinesis_client.exceptions.ResourceNotFoundException:
                pass


def add_entry_to_table(file_details: MockFileDetails, file_status: FileStatus) -> None:
    """Add an entry to the audit table"""
    audit_table_entry = {**file_details.audit_table_entry, "status": {"S": file_status}}
    dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=audit_table_entry)


def deserialize_dynamodb_types(dynamodb_table_entry_with_types):
    """
    Convert a dynamodb table entry with types to a table entry without types
    e.g. {'Attr1': {'S': 'val1'}, 'Attr2': {'N': 'val2'}} becomes  {'Attr1': 'val1'}
    """
    return {
        k: TypeDeserializer().deserialize(v)
        for k, v in dynamodb_table_entry_with_types.items()
    }


def assert_audit_table_entry(
    file_details: FileDetails, expected_status: FileStatus
) -> None:
    """Assert that the file details are in the audit table"""
    table_entry = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME,
        Key={AuditTableKeys.MESSAGE_ID: {"S": file_details.message_id}},
    ).get("Item")
    assert table_entry == {
        **file_details.audit_table_entry,
        "status": {"S": expected_status},
    }
