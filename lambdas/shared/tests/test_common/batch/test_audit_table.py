"""Tests for audit_table functions"""

import unittest
from unittest import TestCase
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_aws

from common.models.errors import UnhandledAuditTableError
from test_common.batch.utils.batch_utils import (
    GenericSetUp,
    GenericTearDown,
    add_entry_to_table,
    assert_audit_table_entry,
)
from test_common.batch.utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)
from test_common.batch.utils.mock_values import (
    FileDetails,
    MockFileDetails,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.batch.audit_table import (
        create_audit_table_item,
        get_record_count_and_failures_by_message_id,
        increment_records_failed_count,
        update_audit_table_item,
    )
    from common.clients import REGION_NAME
    from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.ravs_rsv_1


@mock_aws
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestAuditTable(TestCase):
    """Tests for audit table functions"""

    def setUp(self):
        """Set up test values to be used for the tests"""
        self.logger_patcher = patch("common.batch.audit_table.logger")
        self.mock_logger = self.logger_patcher.start()
        GenericSetUp(dynamo_db_client=dynamodb_client)

    def tearDown(self):
        """Tear down the test values"""
        GenericTearDown(dynamo_db_client=dynamodb_client)
        self.mock_logger.stop()

    @staticmethod
    def get_table_items() -> list:
        """Return all items in the audit table"""

        return dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

    def test_create_audit_table_item(self):
        """Test that the upsert_audit_table function works as expected."""
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26", file_number=1)

        create_audit_table_item(
            message_id=ravs_rsv_test_file.message_id,
            file_key=ravs_rsv_test_file.file_key,
            created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
            queue_name=ravs_rsv_test_file.queue_name,
            file_status=FileStatus.PROCESSED,
            expiry_timestamp=ravs_rsv_test_file.expires_at,
        )

        expected_table_entry = {
            **MockFileDetails.rsv_ravs.audit_table_entry,
            "status": {"S": FileStatus.PROCESSED},
        }

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

        self.assertIn(expected_table_entry, table_items)

    def test_create_audit_table_item_with_duplicate_message_id_raises_exception(self):
        """Test that attempting to create an entry with a message_id that already exists causes an exception"""
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26", file_number=1)

        create_audit_table_item(
            message_id=ravs_rsv_test_file.message_id,
            file_key=ravs_rsv_test_file.file_key,
            created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
            queue_name=ravs_rsv_test_file.queue_name,
            file_status=FileStatus.PROCESSED,
            expiry_timestamp=ravs_rsv_test_file.expires_at,
            condition_expression="attribute_not_exists(message_id)",
        )

        assert_audit_table_entry(ravs_rsv_test_file, FileStatus.PROCESSED)

        with self.assertRaises(UnhandledAuditTableError):
            create_audit_table_item(
                message_id=ravs_rsv_test_file.message_id,
                file_key=ravs_rsv_test_file.file_key,
                created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
                queue_name=ravs_rsv_test_file.queue_name,
                file_status=FileStatus.PROCESSED,
                expiry_timestamp=ravs_rsv_test_file.expires_at,
                condition_expression="attribute_not_exists(message_id)",
            )

    def test_create_audit_table_item_with_duplicate_message_id_no_condition(self):
        """Test that attempting to create an entry with a message_id that already exists causes no exception
        if the condition_expression is not set"""
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26", file_number=1)

        create_audit_table_item(
            message_id=ravs_rsv_test_file.message_id,
            file_key=ravs_rsv_test_file.file_key,
            created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
            queue_name=ravs_rsv_test_file.queue_name,
            file_status=FileStatus.PROCESSING,
            expiry_timestamp=ravs_rsv_test_file.expires_at,
        )

        assert_audit_table_entry(ravs_rsv_test_file, FileStatus.PROCESSING)

        create_audit_table_item(
            message_id=ravs_rsv_test_file.message_id,
            file_key=ravs_rsv_test_file.file_key,
            created_at_formatted_str=ravs_rsv_test_file.created_at_formatted_string,
            queue_name=ravs_rsv_test_file.queue_name,
            file_status=FileStatus.PROCESSED,
            expiry_timestamp=ravs_rsv_test_file.expires_at,
        )

        assert_audit_table_entry(ravs_rsv_test_file, FileStatus.PROCESSED)

    def test_update_audit_table_item_status(self):
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

        update_audit_table_item(
            file_key=file_key, message_id=message_id, optional_params={AuditTableKeys.STATUS: FileStatus.PREPROCESSED}
        )
        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

        self.assertIn(expected_table_entry, table_items)
        self.mock_logger.info.assert_called_once_with(
            "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
            AuditTableKeys.STATUS,
            "RSV_Vaccinations_v5_X26_20210730T12000000.csv",
            "rsv_ravs_test_id",
            "Preprocessed",
        )

    def test_update_audit_table_item_status_including_error_details(self):
        """Checks audit table correctly updates a record including some error details"""
        add_entry_to_table(MockFileDetails.rsv_ravs, file_status=FileStatus.QUEUED)
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")

        update_audit_table_item(
            file_key=ravs_rsv_test_file.file_key,
            message_id=ravs_rsv_test_file.message_id,
            optional_params={
                AuditTableKeys.ERROR_DETAILS: str("Test error details"),
                AuditTableKeys.STATUS: FileStatus.FAILED,
            },
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
        self.mock_logger.info.assert_called_once_with(
            "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
            AuditTableKeys.STATUS,
            "RSV_Vaccinations_v5_X26_20210730T12000000.csv",
            "rsv_ravs_test_id",
            "Failed",
        )

    def test_update_audit_table_item_status_throws_exception_with_invalid_id(self):
        emis_flu_test_file_2 = FileDetails("FLU", "EMIS", "YGM41")

        message_id = emis_flu_test_file_2.message_id
        file_key = emis_flu_test_file_2.file_key

        with self.assertRaises(UnhandledAuditTableError):
            update_audit_table_item(
                file_key=file_key, message_id=message_id, optional_params={AuditTableKeys.STATUS: FileStatus.PROCESSED}
            )

        self.mock_logger.error.assert_called_once()

    def test_update_audit_table_item_ingestion_start_time(self):
        """Checks audit table correctly sets ingestion_start_time to the requested value"""
        add_entry_to_table(MockFileDetails.rsv_ravs, file_status=FileStatus.PROCESSING)

        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")
        file_key = ravs_rsv_test_file.file_key
        message_id = ravs_rsv_test_file.message_id
        test_start_time = "20210730T12100000"

        update_audit_table_item(
            file_key=file_key,
            message_id=message_id,
            optional_params={
                AuditTableKeys.INGESTION_START_TIME: test_start_time,
            },
        )

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])
        self.assertEqual(1, len(table_items))
        self.assertEqual(
            {
                **MockFileDetails.rsv_ravs.audit_table_entry,
                "status": {"S": FileStatus.PROCESSING},
                "ingestion_start_time": {"S": "20210730T12100000"},
            },
            table_items[0],
        )
        self.mock_logger.info.assert_called_once_with(
            "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
            AuditTableKeys.INGESTION_START_TIME,
            "RSV_Vaccinations_v5_X26_20210730T12000000.csv",
            "rsv_ravs_test_id",
            "20210730T12100000",
        )

    def test_update_audit_table_item_ingestion_start_time_throws_exception_with_invalid_id(self):
        emis_flu_test_file_2 = FileDetails("FLU", "EMIS", "YGM41")

        message_id = emis_flu_test_file_2.message_id
        file_key = emis_flu_test_file_2.file_key
        test_start_time = "20210730T12100000"

        with self.assertRaises(UnhandledAuditTableError):
            update_audit_table_item(
                file_key=file_key,
                message_id=message_id,
                optional_params={AuditTableKeys.INGESTION_START_TIME: test_start_time},
            )

        self.mock_logger.error.assert_called_once()

    def test_get_record_count_and_failures_by_message_id_returns_the_record_count_and_failures(self):
        """Test that get_record_count_by_message_id retrieves the integer values of the total record count and
        failures"""
        expected_table_entry = {
            **MockFileDetails.rsv_ravs.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
            "record_count": {"N": "1000"},
            "records_failed": {"N": "5"},
        }
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")
        message_id = ravs_rsv_test_file.message_id

        dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=expected_table_entry)

        record_count, failed_count = get_record_count_and_failures_by_message_id(message_id)

        self.assertEqual(record_count, 1000)
        self.assertEqual(failed_count, 5)

    def test_get_record_count_and_failures_by_message_id_returns_zero_if_values_not_set(self):
        """Test that if the record count has not yet been set on the audit item then zero is returned"""
        expected_table_entry = {
            **MockFileDetails.rsv_ravs.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
        }
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")
        message_id = ravs_rsv_test_file.message_id

        dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=expected_table_entry)

        record_count, failed_count = get_record_count_and_failures_by_message_id(message_id)

        self.assertEqual(record_count, 0)
        self.assertEqual(failed_count, 0)

    def test_increment_records_failed_count(self):
        """Checks audit table correctly increments the records_failed count"""
        expected_table_entry = {
            **MockFileDetails.rsv_ravs.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
        }
        ravs_rsv_test_file = FileDetails("RSV", "RAVS", "X26")
        message_id = ravs_rsv_test_file.message_id

        dynamodb_client.put_item(TableName=AUDIT_TABLE_NAME, Item=expected_table_entry)

        increment_records_failed_count(message_id)

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])
        self.assertEqual(table_items[0]["records_failed"]["N"], "1")


if __name__ == "__main__":
    unittest.main()
