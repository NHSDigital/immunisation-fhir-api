import unittest
from unittest.mock import patch

import audit_table
from common.models.errors import UnhandledAuditTableError
from constants import AUDIT_TABLE_NAME, AuditTableKeys, FileStatus


class TestAuditTable(unittest.TestCase):
    def setUp(self):
        self.logger_patcher = patch("audit_table.logger")
        self.mock_logger = self.logger_patcher.start()
        self.dynamodb_client_patcher = patch("audit_table.dynamodb_client")
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

    def test_get_record_count_by_message_id_returns_the_record_count(self):
        """Test that get_record_count_by_message_id retrieves the integer value of the total record count"""
        test_message_id = "1234"

        self.mock_dynamodb_client.get_item.return_value = {
            "Item": {"message_id": {"S": test_message_id}, "record_count": {"N": "1000"}}
        }

        self.assertEqual(audit_table.get_record_count_by_message_id(test_message_id), 1000)

    def test_get_record_count_by_message_id_returns_none_if_record_count_not_set(self):
        """Test that if the record count has not yet been set on the audit item then None is returned"""
        test_message_id = "1234"

        self.mock_dynamodb_client.get_item.return_value = {"Item": {"message_id": {"S": test_message_id}}}

        self.assertIsNone(audit_table.get_record_count_by_message_id(test_message_id))

    def test_set_records_succeeded_count(self):
        test_message_id = "1234"
        self.mock_dynamodb_client.get_item.return_value = {
            "Item": {"message_id": {"S": test_message_id}, "record_count": {"N": "1000"}, "records_failed": {"N": "42"}}
        }
        audit_table.set_records_succeeded_count(test_message_id)
        self.mock_dynamodb_client.get_item.assert_called_once()
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_message_id}},
            UpdateExpression="SET #counter = :value",
            ExpressionAttributeNames={"#counter": AuditTableKeys.RECORDS_SUCCEEDED},
            ExpressionAttributeValues={":value": {"N": "958"}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        self.mock_logger.info.assert_called_once()

    def test_set_records_succeeded_count_no_failures(self):
        test_message_id = "1234"
        self.mock_dynamodb_client.get_item.return_value = {
            "Item": {"message_id": {"S": test_message_id}, "record_count": {"N": "1000"}}
        }
        audit_table.set_records_succeeded_count(test_message_id)
        self.mock_dynamodb_client.get_item.assert_called_once()
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_message_id}},
            UpdateExpression="SET #counter = :value",
            ExpressionAttributeNames={"#counter": AuditTableKeys.RECORDS_SUCCEEDED},
            ExpressionAttributeValues={":value": {"N": "1000"}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        self.mock_logger.info.assert_called_once()

    def test_set_records_succeeded_count_no_records(self):
        test_message_id = "1234"
        self.mock_dynamodb_client.get_item.return_value = {"Item": {"message_id": {"S": test_message_id}}}
        audit_table.set_records_succeeded_count(test_message_id)
        self.mock_dynamodb_client.get_item.assert_called_once()
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_message_id}},
            UpdateExpression="SET #counter = :value",
            ExpressionAttributeNames={"#counter": AuditTableKeys.RECORDS_SUCCEEDED},
            ExpressionAttributeValues={":value": {"N": "0"}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        self.mock_logger.info.assert_called_once()

    def test_set_records_succeeded_count_raises(self):
        self.mock_dynamodb_client.update_item.side_effect = Exception("fail!")
        with self.assertRaises(UnhandledAuditTableError) as ctx:
            audit_table.set_records_succeeded_count("msg1")
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()

    def test_increment_records_failed_count(self):
        test_message_id = "1234"
        audit_table.increment_records_failed_count(test_message_id)
        self.mock_dynamodb_client.update_item.assert_called_once_with(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_message_id}},
            UpdateExpression="SET #counter = if_not_exists(#counter, :initial) + :increment",
            ExpressionAttributeNames={"#counter": AuditTableKeys.RECORDS_FAILED},
            ExpressionAttributeValues={":increment": {"N": "1"}, ":initial": {"N": "0"}},
            ConditionExpression="attribute_exists(message_id)",
            ReturnValues="UPDATED_NEW",
        )
        self.mock_logger.info.assert_called_once()

    def test_increment_records_failed_count_raises(self):
        self.mock_dynamodb_client.update_item.side_effect = Exception("fail!")
        with self.assertRaises(UnhandledAuditTableError) as ctx:
            audit_table.increment_records_failed_count("msg1")
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()
