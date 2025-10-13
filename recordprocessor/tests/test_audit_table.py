"""Tests for audit_table functions"""

import unittest
from unittest import TestCase
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_dynamodb

from errors import UnhandledAuditTableError
from tests.utils_for_recordprocessor_tests.generic_setup_and_teardown import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    add_entry_to_table,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    FileDetails,
    MockFileDetails,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from audit_table import update_audit_table_status
    from clients import REGION_NAME
    from constants import (
        AUDIT_TABLE_NAME,
        FileStatus,
    )


dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.ravs_rsv_1


@mock_dynamodb
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestAuditTable(TestCase):
    """Tests for audit table functions"""

    def setUp(self):
        """Set up test values to be used for the tests"""
        GenericSetUp(dynamodb_client=dynamodb_client)

    def tearDown(self):
        """Tear down the test values"""
        GenericTearDown(dynamodb_client=dynamodb_client)

    @staticmethod
    def get_table_items() -> list:
        """Return all items in the audit table"""

        return dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

    def test_update_audit_table_status(self):
        """Checks audit table correctly updates a record to the requested status"""
        # Test case 1: file should be updated with status of 'Processed'.

        add_entry_to_table(MockFileDetails.rsv_ravs, file_status=FileStatus.PROCESSING)
        add_entry_to_table(MockFileDetails.flu_emis, file_status=FileStatus.QUEUED)

        expected_table_entry = {
            **MockFileDetails.rsv_ravs.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
        }
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")
        file_key = ravs_rsv_test_file.file_key
        message_id = ravs_rsv_test_file.message_id

        update_audit_table_status(file_key, message_id, FileStatus.PREPROCESSED)
        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

        self.assertIn(expected_table_entry, table_items)

    def test_update_audit_table_status_including_error_details(self):
        """Checks audit table correctly updates a record including some error details"""
        add_entry_to_table(MockFileDetails.rsv_ravs, file_status=FileStatus.QUEUED)
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")

        update_audit_table_status(
            ravs_rsv_test_file.file_key,
            ravs_rsv_test_file.message_id,
            FileStatus.FAILED,
            error_details="Test error details",
        )

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])
        self.assertEqual(1, len(table_items))
        self.assertEqual(
            {
                **MockFileDetails.rsv_ravs.audit_table_entry,
                "status": {"S": FileStatus.FAILED},
                "error_details": {"S": "Test error details"},
            },
            table_items[0],
        )

    def test_update_audit_table_status_throws_exception_with_invalid_id(self):
        emis_flu_test_file_2 = FileDetails("FLU", "EMIS", "YGM41")

        message_id = emis_flu_test_file_2.message_id
        file_key = (emis_flu_test_file_2.file_key,)

        with self.assertRaises(UnhandledAuditTableError):
            update_audit_table_status(file_key, message_id, FileStatus.PROCESSED)


if __name__ == "__main__":
    unittest.main()
