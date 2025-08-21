import unittest
from unittest.mock import patch, MagicMock
import audit_table
from errors import UnhandledAuditTableError

class TestAuditTable(unittest.TestCase):

    def setUp(self):
        self.logger_patcher = patch('audit_table.logger')
        self.mock_logger = self.logger_patcher.start()
        self.dynamodb_resource_patcher = patch('audit_table.dynamodb_resource')
        self.mock_dynamodb_resource = self.dynamodb_resource_patcher.start()
        self.dynamodb_client_patcher = patch('audit_table.dynamodb_client')
        self.mock_dynamodb_client = self.dynamodb_client_patcher.start()

    def tearDown(self):
        self.logger_patcher.stop()
        self.dynamodb_resource_patcher.stop()
        self.dynamodb_client_patcher.stop()

    def test_get_next_queued_file_details_returns_oldest(self):
        # Arrange
        mock_table = MagicMock()
        self.mock_dynamodb_resource.Table.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {"timestamp": 2, "my-key": "value2"},
                {"timestamp": 1, "my-key": "value1"},
            ]
        }
        # Act
        result = audit_table.get_next_queued_file_details("queue1")
        # Assert
        self.assertEqual(result, {"timestamp": 1, "my-key": "value1"})

    def test_get_next_queued_file_details_returns_none_if_empty(self):
        mock_table = MagicMock()
        self.mock_dynamodb_resource.Table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}
        result = audit_table.get_next_queued_file_details("queue1")
        self.assertIsNone(result)

    def test_change_audit_table_status_to_processed_success(self):
        # Should not raise
        self.mock_dynamodb_client.update_item.return_value = {}
        audit_table.change_audit_table_status_to_processed("file1", "msg1")
        self.mock_dynamodb_client.update_item.assert_called_once()
        self.mock_logger.info.assert_called_once()

    def test_change_audit_table_status_to_processed_raises(self):
        self.mock_dynamodb_client.update_item.side_effect = Exception("fail!")
        with self.assertRaises(UnhandledAuditTableError) as ctx:
            audit_table.change_audit_table_status_to_processed("file1", "msg1")
        self.assertIn("fail!", str(ctx.exception))
        self.mock_logger.error.assert_called_once()
