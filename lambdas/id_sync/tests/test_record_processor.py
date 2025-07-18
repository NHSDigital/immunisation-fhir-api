from record_processor import process_record
import unittest
from unittest.mock import patch


class TestRecordProcessor(unittest.TestCase):
    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_record_processor_success(self):
        test_record = "abc1"
        response = process_record(test_record, None)
        self.assertEqual(response, f"hello world {test_record}")
