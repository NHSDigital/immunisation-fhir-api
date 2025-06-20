''' unit tests for redis_sync.py '''
import unittest
from unittest.mock import patch
from redis_sync import handler


class TestHandler(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()
        self.event_processor_patcher = patch("redis_sync.event_processor")
        self.mock_event_processor = self.event_processor_patcher.start()
        self.test_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test-key"}
                    }
                }
            ]
        }
        self.test_context = {}

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.event_processor_patcher.stop()
        self.logger_exception_patcher.stop()

    def test_handler_success(self):
        mock_success = {"result": "ok"}
        self.mock_event_processor.return_value = mock_success
        result = handler(self.test_event, self.test_context)
        self.mock_logger_info.assert_called_with("Sync Handler")
        self.mock_event_processor.assert_called_once_with(self.test_event, self.test_context)
        self.assertEqual(result, mock_success)

    def test_handler_exception(self):
        self.mock_event_processor.side_effect = Exception("fail")
        result = handler(self.test_event, self.test_context)
        self.mock_logger_info.assert_called_with("Sync Handler")
        self.mock_logger_exception.assert_called_with("Error in Redis Sync Processor")
        self.assertFalse(result)
