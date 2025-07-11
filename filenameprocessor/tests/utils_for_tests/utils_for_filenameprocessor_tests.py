"""Utils functions for filenameprocessor tests"""

from unittest.mock import patch
from io import StringIO
from boto3.dynamodb.types import TypeDeserializer
from boto3 import client as boto3_client

from tests.utils_for_tests.values_for_tests import FileDetails, MockFileDetails
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from clients import REGION_NAME
    from csv import DictReader
    from constants import AuditTableKeys, AUDIT_TABLE_NAME, FileStatus

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)


def get_csv_file_dict_reader(s3_client, bucket_name: str, file_key: str) -> DictReader:
    """Download the file from the S3 bucket and return it as a DictReader"""
    ack_file_csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


def deserialize_dynamodb_types(dynamodb_table_entry_with_types):
    """
    Convert a dynamodb table entry with types to a table entry without types
    e.g. {'Attr1': {'S': 'val1'}, 'Attr2': {'N': 'val2'}} becomes  {'Attr1': 'val1'}
    """
    return {k: TypeDeserializer().deserialize(v) for k, v in dynamodb_table_entry_with_types.items()}


def add_entry_to_table(file_details: MockFileDetails, file_status: FileStatus) -> None:
    """Add an entry to the audit table"""
    audit_table_entry = {**file_details.audit_table_entry, "status": {"S": file_status}}
    dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=audit_table_entry)


def assert_audit_table_entry(file_details: FileDetails, expected_status: FileStatus) -> None:
    """Assert that the file details are in the audit table"""
    table_entry = dynamodb_client.get_item(
        TableName=AUDIT_TABLE_NAME, Key={AuditTableKeys.MESSAGE_ID: {"S": file_details.message_id}}
    ).get("Item")
    assert table_entry == {**file_details.audit_table_entry, "status": {"S": expected_status}}
