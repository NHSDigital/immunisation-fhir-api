"""Tests for audit_table functions"""

from unittest import TestCase
from unittest.mock import patch
from boto3 import client as boto3_client
from moto import mock_dynamodb

from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT
from tests.utils_for_tests.generic_setup_and_teardown import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_tests.values_for_tests import MockFileDetails, FileDetails
from tests.utils_for_tests.utils_for_filenameprocessor_tests import (
    deserialize_dynamodb_types,
    add_entry_to_table,
    assert_audit_table_entry,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus
    from audit_table import (
        upsert_audit_table,
        ensure_file_is_not_a_duplicate,
        get_next_queued_file_details,
    )
    from errors import UnhandledAuditTableError, DuplicateFileError
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
        add_entry_to_table(
            MockFileDetails.emis_flu, file_status=FileStatus.QUEUED
        )  # different queue
        add_entry_to_table(
            MockFileDetails.emis_rsv, file_status=FileStatus.QUEUED
        )  # different queue
        add_entry_to_table(
            MockFileDetails.ravs_flu, file_status=FileStatus.QUEUED
        )  # different queue
        add_entry_to_table(
            MockFileDetails.ravs_rsv_1, FileStatus.PROCESSED
        )  # same queue but already processed
        self.assertIsNone(get_next_queued_file_details(queue_to_check))

        # Test case 3: one queued file in the ravs_rsv queue
        add_entry_to_table(MockFileDetails.ravs_rsv_2, file_status=FileStatus.QUEUED)
        expected_table_entry = {
            **MockFileDetails.ravs_rsv_2.audit_table_entry,
            "status": {"S": FileStatus.QUEUED},
        }
        self.assertEqual(
            get_next_queued_file_details(queue_to_check),
            deserialize_dynamodb_types(expected_table_entry),
        )

        # Test case 4: multiple queued files in the RAVS_RSV queue
        # Note that ravs_rsv files 3 and 4 have later timestamps than file 2, so file 2 remains the first in the queue
        add_entry_to_table(MockFileDetails.ravs_rsv_3, file_status=FileStatus.QUEUED)
        add_entry_to_table(MockFileDetails.ravs_rsv_4, file_status=FileStatus.QUEUED)
        self.assertEqual(
            get_next_queued_file_details(queue_to_check),
            deserialize_dynamodb_types(expected_table_entry),
        )

    def test_ensure_file_is_not_a_duplicate(self):
        """
        Tests that ensure_file_is_not_a_duplicate raises a DuplicateFile Error if and only if the file is a
        duplicate in the audit table.
        """
        # Test case 1: file is not a duplicate (and so is not currently in the audit table)
        self.assertIsNone(
            ensure_file_is_not_a_duplicate(
                FILE_DETAILS.file_key, FILE_DETAILS.created_at_formatted_string
            )
        )

        # Add the file to the audit table
        dynamodb_client.put_item(
            TableName=AUDIT_TABLE_NAME,
            Item={
                AuditTableKeys.MESSAGE_ID: {"S": FILE_DETAILS.message_id},
                AuditTableKeys.FILENAME: {"S": FILE_DETAILS.file_key},
                AuditTableKeys.TIMESTAMP: {
                    "S": FILE_DETAILS.created_at_formatted_string
                },
            },
        )

        # Test case 2: file is a duplicate (duplicate file_key, unique creation time)
        with self.assertRaises(DuplicateFileError):
            ensure_file_is_not_a_duplicate(
                FILE_DETAILS.file_key,
                FILE_DETAILS.created_at_formatted_string.replace("2024", "2025"),
            )

    def test_upsert_audit_table(self):
        """
        Test that the upsert_audit_table function works as expected for each anticipated scenario:
        1. New file with status of 'Processed'.
        2. Duplicate file with status of 'Duplicate'.
        3. New file with status of 'Processing', and no files ahead in the queue.
        4. New file with status of 'Processing', and files ahead in the queue.
        5. Existing file with status of 'Processing'.
        6. Existing file with status of 'Processed'.
        7. New file but with duplicated message_id.
        """
        # Populate the table with some entries which are not in the same queue
        add_entry_to_table(
            MockFileDetails.emis_flu, file_status=FileStatus.QUEUED
        )  # different queue
        add_entry_to_table(
            MockFileDetails.emis_rsv, file_status=FileStatus.QUEUED
        )  # different queue
        add_entry_to_table(
            MockFileDetails.ravs_flu, file_status=FileStatus.QUEUED
        )  # different queue

        # Test case 1: new file with status of 'Processed'.
        # File should be added to the audit table, with status 'Processed'. Return value should be False.
        ravs_rsv_test_file_1 = FileDetails("RAVS", "RSV", "YGM41", file_number=1)

        result = upsert_audit_table(
            message_id=ravs_rsv_test_file_1.message_id,
            file_key=ravs_rsv_test_file_1.file_key,
            created_at_formatted_str=ravs_rsv_test_file_1.created_at_formatted_string,
            queue_name=ravs_rsv_test_file_1.queue_name,
            file_status=FileStatus.PROCESSED,
            is_existing_file=False,
        )

        self.assertFalse(result)
        assert_audit_table_entry(ravs_rsv_test_file_1, FileStatus.PROCESSED)

        # Test case 2: Duplicate file with status of 'Duplicate'.
        # Audit table status should be updated to 'Duplicate'. Return value should be False.
        ravs_rsv_test_file_2 = FileDetails("RAVS", "RSV", "YGM41", file_number=2)
        ravs_rsv_test_file_2.file_key = ravs_rsv_test_file_1.file_key
        ravs_rsv_test_file_2.audit_table_entry[AuditTableKeys.FILENAME] = {
            "S": ravs_rsv_test_file_2.file_key
        }

        result = upsert_audit_table(
            message_id=ravs_rsv_test_file_2.message_id,
            file_key=ravs_rsv_test_file_2.file_key,
            created_at_formatted_str=ravs_rsv_test_file_2.created_at_formatted_string,
            queue_name=ravs_rsv_test_file_2.queue_name,
            file_status=FileStatus.DUPLICATE,
            is_existing_file=False,
        )

        self.assertFalse(result)
        assert_audit_table_entry(ravs_rsv_test_file_2, FileStatus.DUPLICATE)

        # Test case 3: new file with status of 'Processing', and no files ahead in the queue.
        # Audit table status should be updated to 'Processing'. Return value should be False.
        ravs_rsv_test_file_3 = FileDetails("RAVS", "RSV", "YGM41", file_number=3)

        result = upsert_audit_table(
            message_id=ravs_rsv_test_file_3.message_id,
            file_key=ravs_rsv_test_file_3.file_key,
            created_at_formatted_str=ravs_rsv_test_file_3.created_at_formatted_string,
            queue_name=ravs_rsv_test_file_3.queue_name,
            file_status=FileStatus.PROCESSING,
            is_existing_file=False,
        )

        self.assertFalse(result)
        assert_audit_table_entry(ravs_rsv_test_file_3, FileStatus.PROCESSING)

        # Test case 4: new file with status of 'Processing', and files ahead in the queue.
        # File should be added to the audit table, with status 'Queued'. Return value should be True.
        rsv_ravs_test_file_4 = FileDetails("RAVS", "RSV", "YGM41", file_number=4)

        result = upsert_audit_table(
            message_id=rsv_ravs_test_file_4.message_id,
            file_key=rsv_ravs_test_file_4.file_key,
            created_at_formatted_str=rsv_ravs_test_file_4.created_at_formatted_string,
            queue_name=rsv_ravs_test_file_4.queue_name,
            file_status=FileStatus.PROCESSING,
            is_existing_file=False,
        )

        self.assertTrue(result)
        assert_audit_table_entry(rsv_ravs_test_file_4, FileStatus.QUEUED)

        # Test case 5: existing file with status of 'Processing'.
        # Audit table status should be updated to 'Processing'. Return value should be False.
        result = upsert_audit_table(
            message_id=rsv_ravs_test_file_4.message_id,
            file_key=rsv_ravs_test_file_4.file_key,
            created_at_formatted_str=rsv_ravs_test_file_4.created_at_formatted_string,
            queue_name=rsv_ravs_test_file_4.queue_name,
            file_status=FileStatus.PROCESSING,
            is_existing_file=True,
        )

        self.assertFalse(result)
        assert_audit_table_entry(rsv_ravs_test_file_4, FileStatus.PROCESSING)

        # Test case 6: existing file with status of 'Processed'.
        # Audit table status should be updated to 'Processed'. Return value should be False.
        result = upsert_audit_table(
            message_id=rsv_ravs_test_file_4.message_id,
            file_key=rsv_ravs_test_file_4.file_key,
            created_at_formatted_str=rsv_ravs_test_file_4.created_at_formatted_string,
            queue_name=rsv_ravs_test_file_4.queue_name,
            file_status=FileStatus.PROCESSED,
            is_existing_file=True,
        )

        self.assertFalse(result)
        assert_audit_table_entry(rsv_ravs_test_file_4, FileStatus.PROCESSED)

        # Test case 7: new file but with duplicated message_id.
        # Audit table status should not be updated. Error should be raised.
        test_file_5 = MockFileDetails.ravs_rsv_5
        test_file_5.message_id = rsv_ravs_test_file_4.message_id
        test_file_5.audit_table_entry[AuditTableKeys.MESSAGE_ID] = (
            test_file_5.message_id
        )

        with self.assertRaises(UnhandledAuditTableError):
            upsert_audit_table(
                message_id=test_file_5.message_id,
                file_key=test_file_5.file_key,
                created_at_formatted_str=test_file_5.created_at_formatted_string,
                queue_name=test_file_5.queue_name,
                file_status=FileStatus.PROCESSED,
                is_existing_file=False,
            )

        # Final reconciliation: ensure that all of the correct items are in the audit table
        table_items = self.get_table_items()
        assert len(table_items) == 7
        assert_audit_table_entry(MockFileDetails.emis_flu, FileStatus.QUEUED)
        assert_audit_table_entry(MockFileDetails.emis_rsv, FileStatus.QUEUED)
        assert_audit_table_entry(MockFileDetails.ravs_flu, FileStatus.QUEUED)
        assert_audit_table_entry(ravs_rsv_test_file_1, FileStatus.PROCESSED)
        assert_audit_table_entry(ravs_rsv_test_file_2, FileStatus.DUPLICATE)
        assert_audit_table_entry(ravs_rsv_test_file_3, FileStatus.PROCESSING)
        assert_audit_table_entry(rsv_ravs_test_file_4, FileStatus.PROCESSED)
