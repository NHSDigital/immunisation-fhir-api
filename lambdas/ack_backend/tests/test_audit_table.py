import unittest
from unittest.mock import patch
import audit_table
from common.models.errors import UnhandledAuditTableError


class TestAuditTable(unittest.TestCase):

    def setUp(self):
        self.logger_patcher = patch('audit_table.logger')
        self.mock_logger = self.logger_patcher.start()
        self.dynamodb_client_patcher = patch('audit_table.dynamodb_client')
        self.mock_dynamodb_client = self.dynamodb_client_patcher.start()

    def tearDown(self):
        self.logger_patcher.stop()
        self.dynamodb_client_patcher.stop()

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
