''' unit tests for id_sync.py '''
import unittest
from unittest.mock import patch
import id_sync


class TestHandler(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()
        self.record_processor_patcher = patch("id_sync.process_record")
        self.mock_record_processor = self.record_processor_patcher.start()
        # patch log_decorator to pass through
        self.mock_log_decorator = patch("common.log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)).start()

    def tearDown(self):
        patch.stopall()

    def test_handler_success(self):
        mock_event = {
            "Records": [
                {"s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "test-key"}}}
            ]
        }
        self.mock_record_processor.return_value = {"file_key": "test-key", "status": "success"}
        response = id_sync.handler(mock_event, None)

        self.assertEqual(response["file_keys"], ["test-key"])
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Successfully processed 1 records")
