"""Tests for audit_table functions"""

import unittest
from unittest import TestCase
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_dynamodb

from common.models.errors import UnhandledAuditTableError
from utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)
from utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
    add_entry_to_table,
)
from utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    FileDetails,
    MockFileDetails,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.batch.audit_table import update_audit_table_item
    from common.clients import REGION_NAME
    from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus

dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.ravs_rsv_1


@mock_dynamodb
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


if __name__ == "__main__":
    unittest.main()
