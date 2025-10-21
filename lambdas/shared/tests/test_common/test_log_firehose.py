import json
import unittest
from datetime import datetime
from unittest.mock import patch

from common.log_firehose import send_log_to_firehose


class TestLogFirehose(unittest.TestCase):
    def setUp(self):
        self.test_stream = "test-stream"
        self.logger_exception_patcher = patch("common.log_firehose.logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()
        self.firehose_client_patcher = patch("common.log_firehose.firehose_client")
        self.mock_firehose_client = self.firehose_client_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_send_log_to_firehose_success(self):
        """Test send_log_to_firehose with successful firehose response"""
        # Arrange
        test_log_data = {"function_name": "test_func", "result": "success"}
        mock_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        self.mock_firehose_client.put_record.return_value = mock_response

        # Act
        send_log_to_firehose(self.test_stream, test_log_data)

        # Assert
        expected_record = {"Data": json.dumps({"event": test_log_data}).encode("utf-8")}
        self.mock_firehose_client.put_record.assert_called_once_with(
            DeliveryStreamName=self.test_stream, Record=expected_record
        )

    def test_send_log_to_firehose_exception(self):
        """Test send_log_to_firehose with firehose exception"""
        # Arrange
        test_log_data = {"function_name": "test_func", "result": "error"}
        self.mock_firehose_client.put_record.side_effect = Exception("Firehose error")

        # Act
        send_log_to_firehose(self.test_stream, test_log_data)

        # Assert
        self.mock_firehose_client.put_record.assert_called_once()
        self.mock_logger_exception.assert_called_once_with(
            "Error sending log to Firehose: %s",
            self.mock_firehose_client.put_record.side_effect,
        )

    def test_send_log_to_firehose_exception_logging(self):
        """Test that logger.exception is called when firehose_client.put_record throws an error"""
        # Arrange
        test_log_data = {"function_name": "test_func", "result": "error"}
        test_error = Exception("Firehose connection failed")
        self.mock_firehose_client.put_record.side_effect = test_error

        # Act
        send_log_to_firehose(self.test_stream, test_log_data)

        # Assert
        # Verify firehose_client.put_record was called
        expected_record = {"Data": json.dumps({"event": test_log_data}).encode("utf-8")}
        self.mock_firehose_client.put_record.assert_called_once_with(
            DeliveryStreamName=self.test_stream, Record=expected_record
        )

        # Verify logger.exception was called with the correct message and error
        self.mock_logger_exception.assert_called_once_with("Error sending log to Firehose: %s", test_error)
