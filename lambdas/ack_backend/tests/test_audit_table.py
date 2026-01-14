import unittest
from unittest.mock import call, patch

import common.batch.audit_table
from common.batch.audit_table import update_audit_table_item
from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus
from common.models.errors import UnhandledAuditTableError


class TestAuditTable(unittest.TestCase):
    def setUp(self):
        self.logger_patcher = patch("common.batch.audit_table.logger")
        self.mock_logger = self.logger_patcher.start()
        self.dynamodb_client_patcher = patch("common.batch.audit_table.dynamodb_client")
        self.mock_dynamodb_client = self.dynamodb_client_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_change_audit_table_status_to_processed_success(self):
        # Should not raise
        update_audit_table_item(
            file_key="file1",
            message_id="msg1",
            optional_params={AuditTableKeys.STATUS: FileStatus.PROCESSED},
        )
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": "msg1"}},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": {"S": FileStatus.PROCESSED}},
            ConditionExpression="attribute_exists(message_id)",
        )
        self.mock_logger.info.assert_called_once()

    def test_change_audit_table_status_to_processed_raises(self):
        self.mock_dynamodb_client.update_item.side_effect = Exception("fail!")
        with self.assertRaises(UnhandledAuditTableError) as ctx:
            update_audit_table_item(file_key="file1", message_id="msg1", optional_params={})
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()

    def test_get_record_count_and_failures_by_message_id_returns_the_record_count_and_failures(self):
        """Test that get_record_count_by_message_id retrieves the integer values of the total record count and
        failures"""
        test_message_id = "1234"
        self.mock_dynamodb_client.get_item.return_value = {
            "Item": {"message_id": {"S": test_message_id}, "record_count": {"N": "1000"}, "records_failed": {"N": "5"}}
        }

        record_count, failed_count = common.batch.audit_table.get_record_count_and_failures_by_message_id(
            test_message_id
        )

        self.assertEqual(record_count, 1000)
        self.assertEqual(failed_count, 5)

    def test_get_record_count_and_failures_by_message_id_returns_zero_if_values_not_set(self):
        """Test that if the record count has not yet been set on the audit item then zero is returned"""
        test_message_id = "1234"

        self.mock_dynamodb_client.get_item.return_value = {"Item": {"message_id": {"S": test_message_id}}}

        record_count, failed_count = common.batch.audit_table.get_record_count_and_failures_by_message_id(
            test_message_id
        )

        self.assertEqual(record_count, 0)
        self.assertEqual(failed_count, 0)

    def test_increment_records_failed_count(self):
        """Checks audit table correctly increments the records_failed count"""
        test_message_id = "1234"
        common.batch.audit_table.increment_records_failed_count(test_message_id)
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_message_id}},
            UpdateExpression="SET #attribute = if_not_exists(#attribute, :initial) + :increment",
            ExpressionAttributeNames={"#attribute": AuditTableKeys.RECORDS_FAILED},
            ExpressionAttributeValues={":increment": {"N": "1"}, ":initial": {"N": "0"}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )

    def test_increment_records_failed_count_raises(self):
        self.mock_dynamodb_client.update_item.side_effect = Exception("fail!")
        with self.assertRaises(UnhandledAuditTableError) as ctx:
            common.batch.audit_table.increment_records_failed_count("msg1")
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()

    def test_set_audit_record_success_count_and_end_time(self):
        """Checks audit table correctly sets ingestion_end_time and success count to the requested value"""
        test_file_key = "RSV_Vaccinations_v5_X26_20210730T12000000.csv"
        test_message_id = "1234"
        test_end_time = "20251208T14430000"
        test_success_count = 5

        update_audit_table_item(
            file_key=test_file_key,
            message_id=test_message_id,
            optional_params={
                AuditTableKeys.INGESTION_END_TIME: test_end_time,
                AuditTableKeys.RECORDS_SUCCEEDED: test_success_count,
            },
        )

        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_message_id}},
            UpdateExpression=(
                f"SET #{AuditTableKeys.INGESTION_END_TIME} = :{AuditTableKeys.INGESTION_END_TIME}"
                f", #{AuditTableKeys.RECORDS_SUCCEEDED} = :{AuditTableKeys.RECORDS_SUCCEEDED}"
            ),
            ExpressionAttributeNames={
                f"#{AuditTableKeys.INGESTION_END_TIME}": AuditTableKeys.INGESTION_END_TIME,
                f"#{AuditTableKeys.RECORDS_SUCCEEDED}": AuditTableKeys.RECORDS_SUCCEEDED,
            },
            ExpressionAttributeValues={
                f":{AuditTableKeys.INGESTION_END_TIME}": {"S": test_end_time},
                f":{AuditTableKeys.RECORDS_SUCCEEDED}": {"N": str(test_success_count)},
            },
            ConditionExpression="attribute_exists(message_id)",
        )
        self.mock_logger.info.assert_has_calls(
            [
                call(
                    "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
                    AuditTableKeys.INGESTION_END_TIME,
                    "RSV_Vaccinations_v5_X26_20210730T12000000.csv",
                    "1234",
                    "20251208T14430000",
                ),
                call(
                    "The %s of file %s, with message id %s, was successfully updated to %s in the audit table",
                    AuditTableKeys.RECORDS_SUCCEEDED,
                    "RSV_Vaccinations_v5_X26_20210730T12000000.csv",
                    "1234",
                    "5",
                ),
            ]
        )

    def test_set_audit_record_success_count_and_end_time_throws_exception_with_invalid_id(self):
        test_file_key = "RSV_Vaccinations_v5_X26_20210730T12000000.csv"
        test_message_id = "1234"
        test_end_time = "20251208T14430000"
        test_success_count = 5
        self.mock_dynamodb_client.update_item.side_effect = Exception("Unhandled error")

        with self.assertRaises(UnhandledAuditTableError) as ctx:
            update_audit_table_item(
                file_key=test_file_key,
                message_id=test_message_id,
                optional_params={
                    AuditTableKeys.RECORDS_SUCCEEDED: test_success_count,
                    AuditTableKeys.INGESTION_END_TIME: test_end_time,
                },
            )
        self.assertIn("Unhandled error", str(ctx.exception))
        self.mock_logger.error.assert_called_once()
