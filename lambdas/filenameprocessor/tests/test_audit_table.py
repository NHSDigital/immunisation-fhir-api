"""Tests for audit_table functions"""

from unittest import TestCase
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_dynamodb

from utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from utils_for_tests.utils_for_filenameprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
    assert_audit_table_entry,
)
from utils_for_tests.values_for_tests import FileDetails, MockFileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from audit_table import upsert_audit_table
    from common.clients import REGION_NAME
    from common.models.errors import UnhandledAuditTableError
    from constants import AUDIT_TABLE_NAME, FileStatus

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.ravs_rsv_1


@mock_dynamodb
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestAuditTable(TestCase):
    """Tests for audit table functions"""

    def setUp(self):
        """Set up test values to be used for the tests"""
        GenericSetUp(dynamodb_client=dynamodb_client)
        self.logger_patcher = patch("audit_table.logger")
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        """Tear down the test values"""
        GenericTearDown(dynamodb_client=dynamodb_client)
        self.logger_patcher.stop()

    @staticmethod
    def get_table_items() -> list:
        """Return all items in the audit table"""
        return dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

    def test_upsert_audit_table(self):
        """Test that the upsert_audit_table function works as expected."""
        ravs_rsv_test_file = FileDetails("RAVS", "RSV", "YGM41", file_number=1)

        upsert_audit_table(
            message_id=ravs_rsv_test_file.message_id,
            file_key=ravs_rsv_test_file.file_key,
            created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
            queue_name=ravs_rsv_test_file.queue_name,
            file_status=FileStatus.PROCESSED,
            expiry_timestamp=ravs_rsv_test_file.expires_at,
        )

        assert_audit_table_entry(ravs_rsv_test_file, FileStatus.PROCESSED)

    def test_upsert_audit_table_with_duplicate_message_id_raises_exception(self):
        """Test that attempting to create an entry with a message_id that already exists causes an exception"""
        ravs_rsv_test_file = FileDetails("RAVS", "RSV", "YGM41", file_number=1)

        upsert_audit_table(
            message_id=ravs_rsv_test_file.message_id,
            file_key=ravs_rsv_test_file.file_key,
            created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
            queue_name=ravs_rsv_test_file.queue_name,
            file_status=FileStatus.PROCESSED,
            expiry_timestamp=ravs_rsv_test_file.expires_at,
        )

        assert_audit_table_entry(ravs_rsv_test_file, FileStatus.PROCESSED)

        with self.assertRaises(UnhandledAuditTableError):
            upsert_audit_table(
                message_id=ravs_rsv_test_file.message_id,
                file_key=ravs_rsv_test_file.file_key,
                created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
                queue_name=ravs_rsv_test_file.queue_name,
                file_status=FileStatus.PROCESSED,
                expiry_timestamp=ravs_rsv_test_file.expires_at,
            )
