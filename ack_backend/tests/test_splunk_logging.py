"""Tests for ack lambda logging decorators"""

import unittest
from unittest.mock import patch, call
import json
from io import StringIO
from contextlib import ExitStack
from moto import mock_s3
from boto3 import client as boto3_client

from tests.utils_for_ack_backend_tests.values_for_ack_backend_tests import (
    ValidValues,
    InvalidValues,
    DiagnosticsDictionaries,
    EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS,
)
from tests.utils_for_ack_backend_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames
from tests.utils_for_ack_backend_tests.generic_setup_and_teardown_for_ack_backend import GenericSetUp, GenericTearDown
from tests.utils_for_ack_backend_tests.utils_for_ack_backend_tests import generate_event

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from ack_processor import lambda_handler

s3_client = boto3_client("s3")


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
class TestLoggingDecorators(unittest.TestCase):
    """Tests for the ack lambda logging decorators"""

    def setUp(self):
        GenericSetUp(s3_client)

        # MOCK SOURCE FILE WITH 100 ROWS TO SIMULATE THE SCENARIO WHERE THE ACK FILE IS NO FULL.
        # TODO: Test all other scenarios.
        mock_source_file_with_100_rows = StringIO("\n".join(f"Row {i}" for i in range(1, 101)))
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{ValidValues.mock_message_expected_log_value.get('file_key')}",
            Body=mock_source_file_with_100_rows.getvalue(),
        )

    def tearDown(self):
        GenericTearDown(s3_client)

    def run(self, result=None):
        """
        This method is run by Unittest, and is being utilised here to apply common patches to all of the tests in the
        class. Using ExitStack allows multiple patches to be applied, whilst ensuring that the mocks are cleaned up
        after the test has run.
        """
        # Set up common patches to be applied to all tests in the class.
        # These patches can be overridden in individual tests.
        common_patches = [
            # NOTE: python3.10/logging/__init__.py file, which is run when logger.info is called, makes a call to
            # time.time. This interferes with patching of the time.time function in these tests.
            # The logging_decorator.logger is patched individually in each test to allow for assertions to be made.
            # Any uses of the logger in other files will confound the tests and should be patched here.
            patch("update_ack_file.logger"),
            # Time is incremented by 1.0 for each call to time.time for ease of testing.
            # Range is set to a large number (100) due to many calls being made to time.time for some tests.
            patch("logging_decorators.time.time", side_effect=[0.0 + i for i in range(100)]),
        ]

        # Set up the ExitStack. Note that patches need to be explicitly started so that they will be applied even when
        # only running one individual test.
        with ExitStack() as stack:
            # datetime.now is patched to return a fixed datetime for ease of testing
            mock_datetime = patch("logging_decorators.datetime").start()
            mock_datetime.now.return_value = ValidValues.fixed_datetime
            stack.enter_context(patch("logging_decorators.datetime", mock_datetime))

            for common_patch in common_patches:
                common_patch.start()
                stack.enter_context(common_patch)

            super().run(result)

    def extract_all_call_args_for_logger_info(self, mock_logger):
        """Extracts all arguments for logger.info."""
        return [args[0] for args, _ in mock_logger.info.call_args_list]

    def extract_all_call_args_for_logger_error(self, mock_logger):
        """Extracts all arguments for logger.error."""
        return [args[0] for args, _ in mock_logger.error.call_args_list]

    def expected_lambda_handler_logs(self, success: bool, number_of_rows, diagnostics=None):
        """Returns the expected logs for the lambda handler function."""
        # Mocking of timings is such that the time taken is 2 seconds for each row, plus 1 second for the handler
        time_taken = f"{number_of_rows * 2 + 1}.0s"
        base_log = (
            ValidValues.lambda_handler_success_expected_log
            if success
            else ValidValues.lambda_handler_failure_expected_log
        )
        return {**base_log, "time_taken": time_taken, **({"diagnostics": diagnostics} if diagnostics else {})}

    def test_splunk_logging_successful_rows(self):
        """Tests a single object in the body of the event"""

        for operation in ["CREATE", "UPDATE", "DELETE"]:
            with (
                patch("logging_decorators.send_log_to_firehose") as mock_send_log_to_firehose,
                patch("logging_decorators.logger") as mock_logger,
            ):
                result = lambda_handler(event=generate_event([{"operation_requested": operation}]), context={})

            self.assertEqual(result, {"statusCode": 200, "body": json.dumps("Lambda function executed successfully!")})

            expected_first_logger_info_data = {
                **ValidValues.mock_message_expected_log_value,
                "operation_requested": operation,
            }

            expected_second_logger_info_data = self.expected_lambda_handler_logs(success=True, number_of_rows=1)

            all_logger_info_call_args = self.extract_all_call_args_for_logger_info(mock_logger)
            first_logger_info_call_args = json.loads(all_logger_info_call_args[0])
            second_logger_info_call_args = json.loads(all_logger_info_call_args[1])
            self.assertEqual(first_logger_info_call_args, expected_first_logger_info_data)
            self.assertEqual(second_logger_info_call_args, expected_second_logger_info_data)

            mock_send_log_to_firehose.assert_has_calls(
                [call(expected_first_logger_info_data), call(expected_second_logger_info_data)]
            )

    def test_splunk_logging_missing_data(self):
        """Tests missing key values in the body of the event"""

        with (
            patch("logging_decorators.send_log_to_firehose") as mock_send_log_to_firehose,
            patch("logging_decorators.logger") as mock_logger,
        ):
            with self.assertRaises(Exception):
                lambda_handler(event={"Records": [{"body": json.dumps([{"": "456"}])}]}, context={})

            expected_first_logger_info_data = {**InvalidValues.Logging_with_no_values}

            expected_first_logger_error_data = self.expected_lambda_handler_logs(
                success=False, number_of_rows=1, diagnostics="'NoneType' object has no attribute 'replace'"
            )

            first_logger_info_call_args = json.loads(self.extract_all_call_args_for_logger_info(mock_logger)[0])
            first_logger_error_call_args = json.loads(self.extract_all_call_args_for_logger_error(mock_logger)[0])
            self.assertEqual(first_logger_info_call_args, expected_first_logger_info_data)
            self.assertEqual(first_logger_error_call_args, expected_first_logger_error_data)

            self.assertEqual(
                mock_send_log_to_firehose.call_args_list,
                [call(expected_first_logger_info_data), call(expected_first_logger_error_data)],
            )

    @patch("logging_decorators.send_log_to_firehose")
    def test_splunk_logging_statuscode_diagnostics(
        self,
        mock_send_log_to_firehose,
    ):
        """'Tests the correct codes are returned for diagnostics"""
        test_cases = [
            {"diagnostics": DiagnosticsDictionaries.RESOURCE_FOUND_ERROR, "expected_code": 409},
            {"diagnostics": DiagnosticsDictionaries.RESOURCE_NOT_FOUND_ERROR, "expected_code": 404},
            {"diagnostics": DiagnosticsDictionaries.MESSAGE_NOT_SUCCESSFUL_ERROR, "expected_code": 500},
            {"diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS, "expected_code": 403},
            {"diagnostics": DiagnosticsDictionaries.IDENTIFIER_DUPLICATION_ERROR, "expected_code": 422},
            {"diagnostics": DiagnosticsDictionaries.UNHANDLED_ERROR, "expected_code": 500},
        ]

        for test_case in test_cases:
            with (
                patch("logging_decorators.send_log_to_firehose") as mock_send_log_to_firehose,
                patch("logging_decorators.logger") as mock_logger,
            ):
                result = lambda_handler(event=generate_event([{"diagnostics": test_case["diagnostics"]}]), context={})

            self.assertEqual(result, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)

            expected_first_logger_info_data = {
                **ValidValues.mock_message_expected_log_value,
                "diagnostics": test_case["diagnostics"].get("error_message"),
                "statusCode": test_case["expected_code"],
                "status": "fail",
            }

            expected_second_logger_info_data = self.expected_lambda_handler_logs(success=True, number_of_rows=1)

            all_logger_info_call_args = self.extract_all_call_args_for_logger_info(mock_logger)
            first_logger_info_call_args = json.loads(all_logger_info_call_args[0])
            second_logger_info_call_args = json.loads(all_logger_info_call_args[1])
            self.assertEqual(first_logger_info_call_args, expected_first_logger_info_data)
            self.assertEqual(second_logger_info_call_args, expected_second_logger_info_data)

            mock_send_log_to_firehose.assert_has_calls(
                [call(expected_first_logger_info_data), call(expected_second_logger_info_data)]
            )

    def test_splunk_logging_multiple_rows(self):
        """Tests logging for multiple objects in the body of the event"""
        messages = [{"row_id": "test1"}, {"row_id": "test2"}]

        with (
            patch("logging_decorators.send_log_to_firehose") as mock_send_log_to_firehose,
            patch("logging_decorators.logger") as mock_logger,
        ):
            result = lambda_handler(generate_event(messages), context={})

        self.assertEqual(result, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)

        expected_first_logger_info_data = {**ValidValues.mock_message_expected_log_value, "message_id": "test1"}

        expected_second_logger_info_data = {**ValidValues.mock_message_expected_log_value, "message_id": "test2"}

        expected_third_logger_info_data = self.expected_lambda_handler_logs(success=True, number_of_rows=2)

        all_logger_info_call_args = self.extract_all_call_args_for_logger_info(mock_logger)
        first_logger_info_call_args = json.loads(all_logger_info_call_args[0])
        second_logger_info_call_args = json.loads(all_logger_info_call_args[1])
        third_logger_info_call_args = json.loads(all_logger_info_call_args[2])
        self.assertEqual(first_logger_info_call_args, expected_first_logger_info_data)
        self.assertEqual(second_logger_info_call_args, expected_second_logger_info_data)
        self.assertEqual(third_logger_info_call_args, expected_third_logger_info_data)

        mock_send_log_to_firehose.assert_has_calls(
            [
                call(expected_first_logger_info_data),
                call(expected_second_logger_info_data),
                call(expected_third_logger_info_data),
            ]
        )

    @patch("logging_decorators.send_log_to_firehose")
    def test_splunk_logging_multiple_with_diagnostics(
        self,
        mock_send_log_to_firehose,
    ):
        """Tests logging for multiple objects in the body of the event with diagnostics"""
        messages = [
            {
                "row_id": "test1",
                "operation_requested": "CREATE",
                "diagnostics": DiagnosticsDictionaries.RESOURCE_FOUND_ERROR,
            },
            {
                "row_id": "test2",
                "operation_requested": "UPDATE",
                "diagnostics": DiagnosticsDictionaries.MESSAGE_NOT_SUCCESSFUL_ERROR,
            },
            {"row_id": "test3", "operation_requested": "DELETE", "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS},
        ]

        with (
            patch("logging_decorators.send_log_to_firehose") as mock_send_log_to_firehose,
            patch("logging_decorators.logger") as mock_logger,
        ):
            result = lambda_handler(generate_event(messages), context={})

        self.assertEqual(result, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)

        expected_first_logger_info_data = {
            **ValidValues.mock_message_expected_log_value,
            "message_id": "test1",
            "operation_requested": "CREATE",
            "statusCode": DiagnosticsDictionaries.RESOURCE_FOUND_ERROR["statusCode"],
            "status": "fail",
            "diagnostics": DiagnosticsDictionaries.RESOURCE_FOUND_ERROR["error_message"],
        }

        expected_second_logger_info_data = {
            **ValidValues.mock_message_expected_log_value,
            "message_id": "test2",
            "operation_requested": "UPDATE",
            "statusCode": DiagnosticsDictionaries.MESSAGE_NOT_SUCCESSFUL_ERROR["statusCode"],
            "status": "fail",
            "diagnostics": DiagnosticsDictionaries.MESSAGE_NOT_SUCCESSFUL_ERROR["error_message"],
        }

        expected_third_logger_info_data = {
            **ValidValues.mock_message_expected_log_value,
            "message_id": "test3",
            "operation_requested": "DELETE",
            "statusCode": DiagnosticsDictionaries.NO_PERMISSIONS["statusCode"],
            "status": "fail",
            "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS["error_message"],
        }

        expected_fourth_logger_info_data = self.expected_lambda_handler_logs(success=True, number_of_rows=3)

        all_logger_info_call_args = self.extract_all_call_args_for_logger_info(mock_logger)
        first_logger_info_call_args = json.loads(all_logger_info_call_args[0])
        second_logger_info_call_args = json.loads(all_logger_info_call_args[1])
        third_logger_info_call_args = json.loads(all_logger_info_call_args[2])
        fourth_logger_info_call_args = json.loads(all_logger_info_call_args[3])
        self.assertEqual(first_logger_info_call_args, expected_first_logger_info_data)
        self.assertEqual(second_logger_info_call_args, expected_second_logger_info_data)
        self.assertEqual(third_logger_info_call_args, expected_third_logger_info_data)
        self.assertEqual(fourth_logger_info_call_args, expected_fourth_logger_info_data)

        mock_send_log_to_firehose.assert_has_calls(
            [
                call(expected_first_logger_info_data),
                call(expected_second_logger_info_data),
                call(expected_third_logger_info_data),
                call(expected_fourth_logger_info_data),
            ]
        )


if __name__ == "__main__":
    unittest.main()
