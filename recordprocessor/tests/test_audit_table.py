"""Tests for audit_table functions"""

from unittest import TestCase
from unittest.mock import patch
from boto3 import client as boto3_client
from moto import mock_dynamodb

from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from tests.utils_for_recordprocessor_tests.generic_setup_and_teardown import GenericSetUp, GenericTearDown
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import MockFileDetails
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    deserialize_dynamodb_types,
    add_entry_to_table,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import (
        AUDIT_TABLE_NAME,
        FileStatus,
    )

    from audit_table import get_next_queued_file_details, change_audit_table_status_to_processed
    from clients import REGION_NAME

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

    def test_get_next_queued_file_details(self):
        """Test that the get_next_queued_file_details function returns the correct file details"""
        # NOTE: Throughout this test the assertions will be checking for the next queued RAVS_RSV file.
        queue_to_check = "RAVS_RSV"

        # Test case 1: no files in audit table
        self.assertIsNone(get_next_queued_file_details(queue_to_check))

        # Test case 2: files in audit table, but none of the files are in the RAVS_RSV queue
        add_entry_to_table(MockFileDetails.flu_emis, file_status=FileStatus.QUEUED)  # different queue
        add_entry_to_table(MockFileDetails.rsv_emis, file_status=FileStatus.QUEUED)  # different queue
        add_entry_to_table(MockFileDetails.ravs_flu, file_status=FileStatus.QUEUED)  # different queue
        add_entry_to_table(MockFileDetails.ravs_rsv_1, FileStatus.PROCESSED)  # same queue but already processed
        self.assertIsNone(get_next_queued_file_details(queue_to_check))

        # Test case 3: one queued file in the ravs_rsv queue
        add_entry_to_table(MockFileDetails.ravs_rsv_2, file_status=FileStatus.QUEUED)
        expected_table_entry = {**MockFileDetails.ravs_rsv_2.audit_table_entry, "status": {"S": FileStatus.QUEUED}}
        self.assertEqual(get_next_queued_file_details(queue_to_check), deserialize_dynamodb_types(expected_table_entry))

        # # Test case 4: multiple queued files in the RAVS_RSV queue
        # Note that ravs_rsv files 3 and 4 have later timestamps than file 2, so file 2 remains the first in the queue
        add_entry_to_table(MockFileDetails.ravs_rsv_3, file_status=FileStatus.QUEUED)
        add_entry_to_table(MockFileDetails.ravs_rsv_4, file_status=FileStatus.QUEUED)
        self.assertEqual(get_next_queued_file_details(queue_to_check), deserialize_dynamodb_types(expected_table_entry))

    def test_change_audit_table_status_to_processed(self):
        """Checks audit table correctly updates a record as processed"""

        add_entry_to_table(MockFileDetails.rsv_ravs, file_status=FileStatus.QUEUED)
        add_entry_to_table(MockFileDetails.flu_emis, file_status=FileStatus.QUEUED)
        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

        expected_table_entry = {**MockFileDetails.rsv_ravs.audit_table_entry, "status": {"S": FileStatus.PROCESSED}}

        file_key = "RSV_Vaccinations_v5_X26_20210730T12000000.csv"
        message_id = "rsv_ravs_test_id_1"

        change_audit_table_status_to_processed(file_key, message_id)
        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

        self.assertIn(expected_table_entry, table_items)
