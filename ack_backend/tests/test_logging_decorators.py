import unittest
from unittest.mock import patch, MagicMock, call
import logging_decorators
import json
import time

class TestLoggingDecorators(unittest.TestCase):
    def setUp(self):
        # Patch logger and firehose_client
        self.logger_patcher = patch('logging_decorators.logger')
        self.mock_logger = self.logger_patcher.start()
        self.firehose_patcher = patch('logging_decorators.firehose_client')
        self.mock_firehose = self.firehose_patcher.start()

    def tearDown(self):
        self.logger_patcher.stop()
        self.firehose_patcher.stop()

    def test_send_log_to_firehose_success(self):
        log_data = {"foo": "bar"}
        logging_decorators.send_log_to_firehose(log_data)
        self.mock_firehose.put_record.assert_called_once()
        self.mock_logger.info.assert_called_with("Log sent to Firehose")

    def test_send_log_to_firehose_exception(self):
        self.mock_firehose.put_record.side_effect = Exception("fail!")
        log_data = {"foo": "bar"}
        logging_decorators.send_log_to_firehose(log_data)
        self.mock_logger.exception.assert_called()
        self.assertIn("Error sending log to Firehose", self.mock_logger.exception.call_args[0][0])

    def test_generate_and_send_logs_info(self):
        start_time = time.time() - 1
        base_log_data = {"base": "data"}
        additional_log_data = {"extra": "info"}
        logging_decorators.generate_and_send_logs(start_time, base_log_data, additional_log_data)
        self.mock_logger.info.assert_called()
        self.mock_firehose.put_record.assert_called_once()

    def test_generate_and_send_logs_error(self):
        start_time = time.time() - 1
        base_log_data = {"base": "data"}
        additional_log_data = {"extra": "info"}
        logging_decorators.generate_and_send_logs(start_time, base_log_data, additional_log_data, is_error_log=True)
        self.mock_logger.error.assert_called()
        self.mock_firehose.put_record.assert_called_once()

    def test_process_diagnostics_dict(self):
        diagnostics = {"statusCode": 400, "error_message": "bad request"}
        result = logging_decorators.process_diagnostics(diagnostics, "file.csv", "msg-1")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(result["diagnostics"], "bad request")

    def test_process_diagnostics_string(self):
        diagnostics = "some error"
        result = logging_decorators.process_diagnostics(diagnostics, "file.csv", "msg-1")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["statusCode"], 500)
        self.assertEqual(result["diagnostics"], "Unable to determine diagnostics issue")

    def test_process_diagnostics_missing_keys(self):
        result = logging_decorators.process_diagnostics(None, "file_key_missing", "unknown")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["statusCode"], 500)
        self.assertIn("unhandled error", result["diagnostics"])

    def test_process_diagnostics_success(self):
        result = logging_decorators.process_diagnostics(None, "file.csv", "msg-1")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("Operation completed successfully", result["diagnostics"])

    def test_convert_message_to_ack_row_logging_decorator_success(self):
        @logging_decorators.convert_message_to_ack_row_logging_decorator
        def dummy_func(message, created_at_formatted_string):
            return "ok"

        message = {
            "file_key": "file.csv",
            "row_id": "row-1",
            "vaccine_type": "type",
            "supplier": "sup",
            "local_id": "loc",
            "operation_requested": "op"
        }
        result = dummy_func(message, "2024-08-20T12:00:00Z")
        self.assertEqual(result, "ok")
        self.mock_logger.info.assert_called()
        self.mock_firehose.put_record.assert_called()

    def test_convert_message_to_ack_row_logging_decorator_exception(self):
        @logging_decorators.convert_message_to_ack_row_logging_decorator
        def dummy_func(message, created_at_formatted_string):
            raise ValueError("fail!")

        message = {
            "file_key": "file.csv",
            "row_id": "row-1",
            "vaccine_type": "type",
            "supplier": "sup",
            "local_id": "loc",
            "operation_requested": "op"
        }
        with self.assertRaises(ValueError):
            dummy_func(message, "2024-08-20T12:00:00Z")
        self.mock_logger.error.assert_called()
        self.mock_firehose.put_record.assert_called()

    def test_ack_lambda_handler_logging_decorator_success(self):
        @logging_decorators.ack_lambda_handler_logging_decorator
        def dummy_lambda(event, context):
            return "lambda-ok"

        result = dummy_lambda({}, {})
        self.assertEqual(result, "lambda-ok")
        self.mock_logger.info.assert_called()
        self.mock_firehose.put_record.assert_called()

    def test_ack_lambda_handler_logging_decorator_exception(self):
        @logging_decorators.ack_lambda_handler_logging_decorator
        def dummy_lambda(event, context):
            raise RuntimeError("fail!")

        with self.assertRaises(RuntimeError):
            dummy_lambda({}, {})
        self.mock_logger.error.assert_called()
        self.mock_firehose.put_record.assert_called()

if __name__ == "__main__":
    unittest.main()