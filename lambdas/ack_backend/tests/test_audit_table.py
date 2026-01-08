import unittest
from unittest.mock import call, patch

import audit_table
from common.models.batch_constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus
from common.models.errors import UnhandledAuditTableError


class TestAuditTable(unittest.TestCase):
    def setUp(self):
        self.logger_patcher = patch("audit_table.logger")
        self.mock_logger = self.logger_patcher.start()
        self.dynamodb_client_patcher = patch("common.clients.global_dynamodb_client")
        self.mock_dynamodb_client = self.dynamodb_client_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_change_audit_table_status_to_processed_success(self):
        # Should not raise
        audit_table.change_audit_table_status_to_processed("file1", "msg1")
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": "msg1"}},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": {"S": FileStatus.PROCESSED}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        self.mock_logger.info.assert_called_once()

    def test_change_audit_table_status_to_processed_raises(self):
        self.mock_dynamodb_client.update_item.side_effect = Exception("fail!")
        with self.assertRaises(UnhandledAuditTableError) as ctx:
            audit_table.change_audit_table_status_to_processed("file1", "msg1")
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()

    def test_get_record_count_and_failures_by_message_id_returns_the_record_count_and_failures(self):
        """Test that get_record_count_by_message_id retrieves the integer values of the total record count and
        failures"""
        test_message_id = "1234"
        self.mock_dynamodb_client.get_item.return_value = {
            "Item": {"message_id": {"S": test_message_id}, "record_count": {"N": "1000"}, "records_failed": {"N": "5"}}
        }

        record_count, failed_count = audit_table.get_record_count_and_failures_by_message_id(test_message_id)

        self.assertEqual(record_count, 1000)
        self.assertEqual(failed_count, 5)

    def test_get_record_count_and_failures_by_message_id_returns_zero_if_values_not_set(self):
        """Test that if the record count has not yet been set on the audit item then zero is returned"""
        test_message_id = "1234"

        self.mock_dynamodb_client.get_item.return_value = {"Item": {"message_id": {"S": test_message_id}}}

        record_count, failed_count = audit_table.get_record_count_and_failures_by_message_id(test_message_id)

        self.assertEqual(record_count, 0)
        self.assertEqual(failed_count, 0)

    def test_increment_records_failed_count(self):
        """Checks audit table correctly increments the records_failed count"""
        test_message_id = "1234"
        audit_table.increment_records_failed_count(test_message_id)
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
            audit_table.increment_records_failed_count("msg1")
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()

    def test_set_audit_record_success_count_and_end_time(self):
        """Checks audit table correctly sets ingestion_end_time and success count to the requested value"""
        test_file_key = "RSV_Vaccinations_v5_X26_20210730T12000000.csv"
        test_message_id = "1234"
        test_end_time = "20251208T14430000"
        test_success_count = 5

        audit_table.set_audit_record_success_count_and_end_time(
            test_file_key, test_message_id, test_success_count, test_end_time
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
                    "ingestion_end_time for %s file, with message id %s, was successfully updated to %s in the audit table",
                    "RSV_Vaccinations_v5_X26_20210730T12000000.csv",
                    "1234",
                    "20251208T14430000",
                ),
                call(
                    "records_succeeded for %s file, with message id %s, was successfully updated to %s in the audit table",
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
            audit_table.set_audit_record_success_count_and_end_time(
                test_file_key, test_message_id, test_success_count, test_end_time
            )
        self.assertIn("Unhandled error", str(ctx.exception))
        self.mock_logger.error.assert_called_once()
