import unittest
from unittest.mock import patch
import json
from datetime import datetime

from common.log_decorator import logging_decorator, generate_and_send_logs, send_log_to_firehose


class TestLogDecorator(unittest.TestCase):

    def setUp(self):
        self.test_stream = "test-stream"
        self.test_prefix = "test"

    @patch("common.log_decorator.firehose_client")
    @patch("common.log_decorator.logger")
    def test_send_log_to_firehose_success(self, mock_logger, mock_firehose_client):
        """Test send_log_to_firehose with successful firehose response"""
        # Arrange
        test_log_data = {"function_name": "test_func", "result": "success"}
        mock_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_firehose_client.put_record.return_value = mock_response

        # Act
        send_log_to_firehose(self.test_stream, test_log_data)

        # Assert
        expected_record = {"Data": json.dumps({"event": test_log_data}).encode("utf-8")}
        mock_firehose_client.put_record.assert_called_once_with(
            DeliveryStreamName=self.test_stream, 
            Record=expected_record
        )
        mock_logger.info.assert_called_once_with("Log sent to Firehose: %s", mock_response)
        mock_logger.exception.assert_not_called()

    @patch("common.log_decorator.firehose_client")
    @patch("common.log_decorator.logger")
    def test_send_log_to_firehose_exception(self, mock_logger, mock_firehose_client):
        """Test send_log_to_firehose with firehose exception"""
        # Arrange
        test_log_data = {"function_name": "test_func", "result": "error"}
        mock_firehose_client.put_record.side_effect = Exception("Firehose error")

        # Act
        send_log_to_firehose(self.test_stream, test_log_data)

        # Assert
        mock_firehose_client.put_record.assert_called_once()
        mock_logger.exception.assert_called_once_with(
            "Error sending log to Firehose: %s", 
            mock_firehose_client.put_record.side_effect
        )
        mock_logger.info.assert_not_called()

    @patch("common.log_decorator.send_log_to_firehose")
    @patch("common.log_decorator.logger")
    @patch("time.time")
    def test_generate_and_send_logs_success(self, mock_time, mock_logger, mock_send_log):
        """Test generate_and_send_logs with successful log generation"""
        # Arrange
        mock_time.return_value = 1000.5
        start_time = 1000.0
        base_log_data = {"function_name": "test_func", "date_time": "2023-01-01"}
        additional_log_data = {"statusCode": 200, "result": "success"}

        # Act
        generate_and_send_logs(self.test_stream, start_time, base_log_data, additional_log_data)

        # Assert
        expected_log_data = {
            "function_name": "test_func",
            "date_time": "2023-01-01",
            "time_taken": "0.5s",
            "statusCode": 200,
            "result": "success"
        }
        mock_logger.info.assert_called_once_with(json.dumps(expected_log_data))
        mock_logger.error.assert_not_called()
        mock_send_log.assert_called_once_with(self.test_stream, expected_log_data)

    @patch("common.log_decorator.send_log_to_firehose")
    @patch("common.log_decorator.logger")
    @patch("time.time")
    def test_generate_and_send_logs_error(self, mock_time, mock_logger, mock_send_log):
        """Test generate_and_send_logs with error log generation"""
        # Arrange
        mock_time.return_value = 1000.75
        start_time = 1000.0
        base_log_data = {"function_name": "test_func", "date_time": "2023-01-01"}
        additional_log_data = {"statusCode": 500, "error": "Test error"}

        # Act
        generate_and_send_logs(self.test_stream, start_time, base_log_data, additional_log_data, is_error_log=True)

        # Assert
        expected_log_data = {
            "function_name": "test_func",
            "date_time": "2023-01-01",
            "time_taken": "0.75s",
            "statusCode": 500,
            "error": "Test error"
        }
        mock_logger.error.assert_called_once_with(json.dumps(expected_log_data))
        mock_logger.info.assert_not_called()
        mock_send_log.assert_called_once_with(self.test_stream, expected_log_data)

    @patch("common.log_decorator.generate_and_send_logs")
    @patch("common.log_decorator.logger")
    @patch("common.log_decorator.time")
    @patch("common.log_decorator.datetime")
    def test_logging_decorator_success(self, mock_datetime, mock_time, mock_logger, mock_generate_send):
        """Test logging_decorator with successful function execution"""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        mock_time.time.return_value = 1000.0
        mock_generate_send.return_value = None

        @logging_decorator(self.test_prefix, self.test_stream)
        def test_function(x, y):
            return {"statusCode": 200, "result": x + y}

        # Act
        result = test_function(2, 3)

        # Assert
        self.assertEqual(result, {"statusCode": 200, "result": 5})
        mock_logger.info.assert_called_once_with("Starting function: %s", "test_function")

        # Verify generate_and_send_logs was called with correct parameters
        mock_generate_send.assert_called_once()
        call_args = mock_generate_send.call_args[0]
        call_kwargs = mock_generate_send.call_args[1]
        self.assertEqual(call_args[0], self.test_stream)  # stream_name
        self.assertEqual(call_args[1], 1000.0)  # start_time
        self.assertEqual(call_args[2]["function_name"], f"{self.test_prefix}_test_function")  # base_log_data
        self.assertEqual(call_kwargs['additional_log_data'], {"statusCode": 200, "result": 5})  # additional_log_data
        self.assertNotIn("is_error_log", call_kwargs)  # Should not be error log

    @patch("common.log_decorator.generate_and_send_logs")
    @patch("common.log_decorator.logger")
    @patch("common.log_decorator.time")
    @patch("common.log_decorator.datetime")
    def test_logging_decorator_exception(self, mock_datetime, mock_time, mock_logger, mock_generate_send):
        """Test logging_decorator with function raising exception"""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        mock_time.time.return_value = 1000.0
        mock_generate_send.return_value = None

        @logging_decorator(self.test_prefix, self.test_stream)
        def test_function_with_error():
            raise ValueError("Test error")

        # Act & Assert
        with self.assertRaises(ValueError):
            test_function_with_error()

        mock_logger.info.assert_called_once_with("Starting function: %s", "test_function_with_error")

        # Verify generate_and_send_logs was called with error parameters
        mock_generate_send.assert_called_once()
        call_args = mock_generate_send.call_args[0]
        call_kwargs = mock_generate_send.call_args[1]

        self.assertEqual(call_args[0], self.test_stream)  # stream_name
        self.assertEqual(call_args[1], 1000.0)  # start_time
        self.assertEqual(call_args[2]["function_name"], f"{self.test_prefix}_test_function_with_error")  # base_log_data
        self.assertEqual(call_args[3], {"statusCode": 500, "error": "Test error"})  # additional_log_data
        self.assertTrue(call_kwargs.get("is_error_log", False))  # Should be error log

    @patch("common.log_decorator.generate_and_send_logs")
    @patch("common.log_decorator.logger")
    def test_logging_decorator_preserves_function_metadata(self, mock_logger, mock_generate_send):
        """Test that the decorator preserves the original function's metadata"""
        # Arrange
        mock_generate_send.return_value = None

        @logging_decorator(self.test_prefix, self.test_stream)
        def documented_function():
            """This is a test function with documentation"""
            return "test"

        # Act & Assert
        self.assertEqual(documented_function.__name__, "documented_function")
        self.assertEqual(documented_function.__doc__, "This is a test function with documentation")

