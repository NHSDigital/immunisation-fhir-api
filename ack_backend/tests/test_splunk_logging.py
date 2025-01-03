import unittest
from unittest.mock import patch, MagicMock
import json
import copy
from datetime import datetime
from src.ack_processor import lambda_handler
from tests.test_utils_for_ack_backend import ValidValues, InvalidValues
from update_ack_file import update_ack_file, obtain_current_ack_content, upload_ack_file
from log_firehose_splunk import FirehoseLogger
from log_structure_splunk import logger


class TestSplunkFunctionInfo(unittest.TestCase):

    def setUp(self):
        self.message_body_base = {"Records": [{"body": json.dumps([ValidValues.DPSFULL_ack_processor_input])}]}

        self.message_body_two_base = {
            "Records": [
                {
                    "body": json.dumps(
                        [
                            ValidValues.DPSFULL_ack_processor_input,
                            ValidValues.EMIS_ack_processor_input,
                        ]
                    )
                }
            ]
        }

    def extract_log_json(self, log_entry):
        """Extracts JSON from log entry."""
        json_start = log_entry.find("{")
        json_str = log_entry[json_start:]
        return json.loads(json_str)

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("log_structure_splunk.firehose_logger")
    @patch("time.time")
    @patch("log_structure_splunk.datetime")
    def test_splunk_logging_successful_rows(
        self,
        mock_datetime,
        mock_time,
        mock_firehose_logger,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests a single object in the body of the event"""
        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 9, 1)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}
        operations = [
            {"operation_request": "CREATE"},
            {"operation_request": "UPDATE"},
            {"operation_request": "DELETE"},
        ]

        for op in operations:
            with self.assertLogs(level="INFO") as log:
                message_body = copy.deepcopy(self.message_body_base)

                for record in message_body["Records"]:
                    body_data = json.loads(record["body"])
                    for item in body_data:
                        item["action_flag"] = op["operation_request"]
                    record["body"] = json.dumps(body_data)

                context = {}

                result = lambda_handler(message_body, context)
                self.assertIn("200", str(result["statusCode"]))
                self.assertGreater(len(log.output), 0)

                log_json = self.extract_log_json(log.output[0])
                expected_values = copy.deepcopy(ValidValues.DPSFULL_expected_log_value)
                expected_values["operation_requested"] = op["operation_request"]
                expected_values["time_taken"] = "1.0s"

                for key, expected in expected_values.items():
                    self.assertEqual(log_json[key], expected)

                mock_firehose_logger.ack_send_log.assert_called_once_with({"event": log_json})
                mock_firehose_logger.ack_send_log.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("log_structure_splunk.firehose_logger")
    @patch("time.time")
    @patch("log_structure_splunk.datetime")
    def test_splunk_logging_missing_data(
        self,
        mock_datetime,
        mock_time,
        mock_firehose_logger,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests missing key values in the body of the event"""
        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 9, 1)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}

        with self.assertLogs(level="INFO") as log:
            message_body = {"Records": [{"body": json.dumps([{"": "456"}])}]}

            context = {}

            result = lambda_handler(message_body, context)
            self.assertIn("200", str(result["statusCode"]))
            self.assertGreater(len(log.output), 0)

            log_json = self.extract_log_json(log.output[0])
            expected_values = copy.deepcopy(InvalidValues.Logging_with_no_values)
            expected_values["time_taken"] = "1.0s"

            for key, expected in expected_values.items():
                self.assertEqual(log_json.get(key, "unknown"), expected)

            mock_firehose_logger.ack_send_log.assert_called_once_with({"event": log_json})
            mock_firehose_logger.ack_send_log.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("log_structure_splunk.firehose_logger")
    @patch("time.time")
    @patch("log_structure_splunk.datetime")
    def test_splunk_logging_statuscode_diagnostics(
        self,
        mock_datetime,
        mock_time,
        mock_firehose_logger,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """'Tests the correct codes are returned for diagnostics"""

        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 18, 1)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}
        operations = [
            {"diagnostic": "application includes invalid authorization values", "expected_code": 500},
            {"diagnostic": "Does not exist.", "expected_code": 404},
            {"diagnostic": "unhandled error", "expected_code": 500},
            {"diagnostic": "unauthorized to access", "expected_code": 403},
            {"diagnostic": "duplicate", "expected_code": 422},
            {"diagnostic": "some other error in validation", "expected_code": 400},
        ]

        for op in operations:
            with self.assertLogs(level="INFO") as log:
                message_body = copy.deepcopy(self.message_body_base)

                for record in message_body["Records"]:
                    body_data = json.loads(record["body"])
                    for item in body_data:
                        item["diagnostics"] = op["diagnostic"]
                    record["body"] = json.dumps(body_data)
                context = {}

                result = lambda_handler(message_body, context)
                self.assertIn("200", str(result["statusCode"]))
                self.assertGreater(len(log.output), 0)

                log_json = self.extract_log_json(log.output[0])
                expected_values = copy.deepcopy(ValidValues.DPSFULL_expected_log_value)
                expected_values["diagnostics"] = op["diagnostic"]
                expected_values["statusCode"] = op["expected_code"]
                expected_values["status"] = "fail"
                expected_values["time_taken"] = "1.0s"

                for key, expected in expected_values.items():
                    self.assertEqual(log_json[key], expected)

                mock_firehose_logger.ack_send_log.assert_called_once_with({"event": log_json})
                mock_firehose_logger.ack_send_log.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("log_structure_splunk.firehose_logger")
    @patch("time.time")
    @patch("log_structure_splunk.datetime")
    def test_splunk_logging_multiple_rows(
        self,
        mock_datetime,
        mock_time,
        mock_firehose_logger,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests logging for multiple objects in the body of the event"""
        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(9)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}

        with self.assertLogs(level="INFO") as log:
            message_body = copy.deepcopy(self.message_body_two_base)
            for record in message_body["Records"]:
                body_data = json.loads(record["body"])
                record["body"] = json.dumps(body_data)

            context = {}
            result = lambda_handler(message_body, context)
            self.assertIn("200", str(result["statusCode"]))

            self.assertEqual(len(log.output), 2)
            log_entries = [self.extract_log_json(entry) for entry in log.output]

            expected_entries = [
                copy.deepcopy(ValidValues.DPSFULL_expected_log_value),
                copy.deepcopy(ValidValues.EMIS_expected_log_value),
            ]

            for idx, entry in enumerate(log_entries):
                for key, expected in expected_entries[idx].items():
                    self.assertEqual(entry[key], expected)

            self.assertEqual(mock_firehose_logger.ack_send_log.call_count, 2)
            mock_firehose_logger.ack_send_log.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("log_structure_splunk.firehose_logger")
    @patch("time.time")
    @patch("log_structure_splunk.datetime")
    def test_splunk_logging_multiple_with_diagnostics(
        self,
        mock_datetime,
        mock_time,
        mock_firehose_logger,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests logging for multiple objects in the body of the event with diagnostics"""

        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(27)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}
        operations = [
            {"operation_request": "CREATE", "diagnostics": "application includes invalid authorization values"},
            {"operation_request": "UPDATE", "diagnostics": "some_update_diagnostic"},
            {"operation_request": "DELETE", "diagnostics": "some_delete_diagnostic"},
        ]

        for op in operations:
            with self.assertLogs(level="INFO") as log:
                message_body = copy.deepcopy(self.message_body_two_base)

                for record in message_body["Records"]:
                    body_data = json.loads(record["body"])
                    for item in body_data:
                        item["action_flag"] = op["operation_request"]
                        item["diagnostics"] = op["diagnostics"]
                    record["body"] = json.dumps(body_data)

                context = {}
                result = lambda_handler(message_body, context)

                self.assertIn("200", str(result["statusCode"]))

                self.assertEqual(len(log.output), 2)
                for record_log in log.output:
                    log_json = self.extract_log_json(record_log)
                    self.assertEqual(log_json["operation_requested"], op["operation_request"])
                    self.assertEqual(log_json["diagnostics"], op["diagnostics"])

                self.assertEqual(mock_firehose_logger.ack_send_log.call_count, 2)
                mock_firehose_logger.ack_send_log.reset_mock()


if __name__ == "__main__":
    unittest.main()
