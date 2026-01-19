"""Utils for the audit table tests"""

from typing import Optional
from unittest.mock import patch

from boto3 import client as boto3_client

from test_common.batch.utils.mock_values import (
    FileDetails,
    MockFileDetails,
)
from test_common.testing_utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)


class GenericSetUp:
    """
    Performs generic setup of mock resources
    """

    def __init__(
        self,
        dynamo_db_client=None,
    ):
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
        dynamo_db_client=None,
    ):
        if dynamo_db_client:
            dynamo_db_client.delete_table(TableName=AUDIT_TABLE_NAME)


def add_entry_to_table(file_details: MockFileDetails, file_status: str) -> None:
    """Add an entry to the audit table"""
    audit_table_entry = {**file_details.audit_table_entry, "status": {"S": file_status}}
    dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=audit_table_entry)


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
