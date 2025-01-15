import unittest
from unittest.mock import patch, call
import json
import copy
from src.ack_processor import lambda_handler
from tests.test_utils_for_ack_backend import ValidValues, InvalidValues, DiagnosticsDictionaries


class TestSplunkFunctionInfo(unittest.TestCase):

    def setUp(self):
        self.message_body_base = {"Records": [{"body": json.dumps([ValidValues.DPSFULL_ack_processor_input])}]}

        self.message_body_two_base = {
            "Records": [
                {
                    "body": json.dumps(
                        [
                            ValidValues.DPSFULL_ack_processor_input,
                            ValidValues.DPSFULL_ack_processor_input,
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
    @patch("logging_decorators.send_log_to_firehose")
    @patch("time.time")
    @patch("logging_decorators.datetime")
    def test_splunk_logging_successful_rows(
        self,
        mock_datetime,
        mock_time,
        mock_send_log_to_firehose,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests a single object in the body of the event"""
        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 24, 1)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}
        operations = [
            {"operation_request": "CREATE"},
            {"operation_request": "UPDATE"},
            {"operation_request": "DELETE"},
        ]

        for operation in operations:
            with self.assertLogs(level="INFO") as log:
                message_body = copy.deepcopy(self.message_body_base)

                for record in message_body["Records"]:
                    body_data = json.loads(record["body"])
                    for item in body_data:
                        item["operation_requested"] = operation["operation_request"]
                    record["body"] = json.dumps(body_data)

                context = {}
                result = lambda_handler(message_body, context)
                self.assertIn("200", str(result["statusCode"]))
                self.assertGreater(len(log.output), 0)

                log_json = self.extract_log_json(log.output[0])
                expected_values = copy.deepcopy(ValidValues.DPSFULL_expected_log_value)
                expected_values["operation_requested"] = operation["operation_request"]
                expected_values["time_taken"] = "1.0s"

                for key, expected in expected_values.items():
                    self.assertEqual(log_json[key], expected)
                mock_send_log_to_firehose.assert_has_calls([call(log_json)])
                mock_send_log_to_firehose.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("logging_decorators.send_log_to_firehose")
    @patch("time.time")
    @patch("logging_decorators.datetime")
    def test_splunk_logging_missing_data(
        self,
        mock_datetime,
        mock_time,
        mock_send_log_to_firehose,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests missing key values in the body of the event"""
        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 12, 1)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}

        with self.assertLogs(level="INFO") as log:
            message_body = {"Records": [{"body": json.dumps([{"": "456"}])}]}

            context = {}

            with self.assertRaises(Exception):
                lambda_handler(message_body, context)

            self.assertGreater(len(log.output), 0)

            log_json = self.extract_log_json(log.output[0])
            expected_values = copy.deepcopy(InvalidValues.Logging_with_no_values)
            expected_values["time_taken"] = "1.0s"

            for key, expected in expected_values.items():
                self.assertEqual(log_json.get(key, "unknown"), expected)

            # TODO: ? Test for second firehose call
            mock_send_log_to_firehose.assert_has_calls([call(log_json)])
            mock_send_log_to_firehose.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("logging_decorators.send_log_to_firehose")
    @patch("time.time")
    @patch("logging_decorators.datetime")
    def test_splunk_logging_statuscode_diagnostics(
        self,
        mock_datetime,
        mock_time,
        mock_send_log_to_firehose,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """'Tests the correct codes are returned for diagnostics"""

        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 48, 1)]

        mock_create_ack_data.return_value = None
        mock_update_ack_file.return_value = {}
        operations = [
            {"diagnostics": DiagnosticsDictionaries.RESOURCE_FOUND_ERROR, "expected_code": 409},
            {"diagnostics": DiagnosticsDictionaries.RESOURCE_NOT_FOUND_ERROR, "expected_code": 404},
            {"diagnostics": DiagnosticsDictionaries.MESSAGE_NOT_SUCCESSFUL_ERROR, "expected_code": 500},
            {"diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS, "expected_code": 403},
            {"diagnostics": DiagnosticsDictionaries.IDENTIFIER_DUPLICATION_ERROR, "expected_code": 422},
            {"diagnostics": DiagnosticsDictionaries.UNHANDLED_ERROR, "expected_code": 500},
        ]

        for operation in operations:
            with self.assertLogs(level="INFO") as log:
                message_body = copy.deepcopy(self.message_body_base)

                for record in message_body["Records"]:
                    body_data = json.loads(record["body"])
                    for item in body_data:
                        item["diagnostics"] = operation["diagnostics"]
                    record["body"] = json.dumps(body_data)
                context = {}

                result = lambda_handler(message_body, context)
                self.assertIn("200", str(result["statusCode"]))
                self.assertGreater(len(log.output), 0)

                log_json = self.extract_log_json(log.output[0])
                expected_values = copy.deepcopy(ValidValues.DPSFULL_expected_log_value)
                expected_values["diagnostics"] = operation["diagnostics"].get("error_message")
                expected_values["statusCode"] = operation["expected_code"]
                expected_values["status"] = "fail"
                expected_values["time_taken"] = "1.0s"

                for key, expected in expected_values.items():
                    self.assertEqual(log_json[key], expected)

                mock_send_log_to_firehose.assert_has_calls([call(log_json)])
                mock_send_log_to_firehose.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("logging_decorators.send_log_to_firehose")
    @patch("time.time")
    @patch("logging_decorators.datetime")
    def test_splunk_logging_multiple_rows(
        self,
        mock_datetime,
        mock_time,
        mock_send_log_to_firehose,
        mock_update_ack_file,
        mock_create_ack_data,
        mock_obtain_current_ack_content,
        mock_upload_ack_file,
    ):
        """Tests logging for multiple objects in the body of the event"""
        mock_datetime.now.return_value = ValidValues.fixed_datetime
        mock_time.side_effect = [100000.0 + i for i in range(0, 12, 1)]
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

            self.assertEqual(len(log.output), 3)
            log_entries = [self.extract_log_json(entry) for entry in log.output]

            expected_entries = [
                copy.deepcopy(ValidValues.DPSFULL_expected_log_value),
                copy.deepcopy(ValidValues.DPSFULL_expected_log_value),
            ]

            for idx, entry in enumerate(log_entries[:2]):
                for key, expected in expected_entries[idx].items():
                    self.assertEqual(entry[key], expected)

            self.assertEqual(mock_send_log_to_firehose.call_count, 3)
            mock_send_log_to_firehose.reset_mock()

    @patch("update_ack_file.upload_ack_file")
    @patch("update_ack_file.obtain_current_ack_content")
    @patch("ack_processor.create_ack_data")
    @patch("ack_processor.update_ack_file")
    @patch("logging_decorators.send_log_to_firehose")
    @patch("time.time")
    @patch("logging_decorators.datetime")
    def test_splunk_logging_multiple_with_diagnostics(
        self,
        mock_datetime,
        mock_time,
        mock_send_log_to_firehose,
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
            {"operation_request": "CREATE", "diagnostics": DiagnosticsDictionaries.RESOURCE_FOUND_ERROR},
            {"operation_request": "UPDATE", "diagnostics": DiagnosticsDictionaries.MESSAGE_NOT_SUCCESSFUL_ERROR},
            {"operation_request": "DELETE", "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS},
        ]

        for op in operations:
            with self.assertLogs(level="INFO") as log:
                message_body = copy.deepcopy(self.message_body_two_base)

                for record in message_body["Records"]:
                    body_data = json.loads(record["body"])
                    for item in body_data:
                        item["operation_requested"] = op["operation_request"]
                        item["diagnostics"] = op["diagnostics"]
                    record["body"] = json.dumps(body_data)

                context = {}
                result = lambda_handler(message_body, context)

                self.assertIn("200", str(result["statusCode"]))

                self.assertEqual(len(log.output), 3)

                for record_log in log.output[:2]:
                    log_json = self.extract_log_json(record_log)
                    self.assertEqual(log_json["operation_requested"], op["operation_request"])
                    self.assertEqual(log_json["diagnostics"], op["diagnostics"].get("error_message"))

                self.assertEqual(mock_send_log_to_firehose.call_count, 3)
                mock_send_log_to_firehose.reset_mock()


if __name__ == "__main__":
    unittest.main()
