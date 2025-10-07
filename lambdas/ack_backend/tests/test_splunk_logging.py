"""Tests for ack lambda logging decorators"""
import unittest
from unittest.mock import patch, call
import json
from io import StringIO
from contextlib import ExitStack
from moto import mock_s3
from boto3 import client as boto3_client

from tests.utils.values_for_ack_backend_tests import (
    ValidValues,
    InvalidValues,
    DiagnosticsDictionaries,
    EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS,
)
from tests.utils.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames
from tests.utils.generic_setup_and_teardown_for_ack_backend import GenericSetUp, GenericTearDown
from tests.utils.utils_for_ack_backend_tests import generate_event

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from ack_processor import lambda_handler


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
class TestLoggingDecorators(unittest.TestCase):
    """Tests for the ack lambda logging decorators"""

    def setUp(self):
        self.s3_client = boto3_client("s3", region_name="eu-west-2")
        GenericSetUp(self.s3_client)
        self.stream_name = MOCK_ENVIRONMENT_DICT["FIREHOSE_STREAM_NAME"]

        # MOCK SOURCE FILE WITH 100 ROWS TO SIMULATE THE SCENARIO WHERE THE ACK FILE IS NO FULL.
        # TODO: Test all other scenarios.
        mock_source_file_with_100_rows = StringIO("\n".join(f"Row {i}" for i in range(1, 101)))
        self.s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{ValidValues.mock_message_expected_log_value.get('file_key')}",
            Body=mock_source_file_with_100_rows.getvalue(),
        )

    def tearDown(self):
        GenericTearDown(self.s3_client)

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
            # Range is set to a large number (300) due to many calls being made to time.time for some tests.
            patch("logging_decorators.time.time", side_effect=[0.0 + i for i in range(300)]),
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

    def expected_lambda_handler_logs(self, success: bool, number_of_rows, ingestion_complete=False, diagnostics=None):
        """Returns the expected logs for the lambda handler function."""
        # Mocking of timings is such that the time taken is 2 seconds for each row,
        # plus 2 seconds for the handler if it succeeds (i.e. it calls update_ack_file) or 1 second if it doesn't;
        # plus an extra second if ingestion is complete
        if success:
            time_taken = f"{number_of_rows * 2 + 3}.0s" if ingestion_complete else f"{number_of_rows * 2 + 2}.0s"
        else:
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
            with (  # noqa: E999
                patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
                patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
            ):  # noqa: E999
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
                [
                    call(self.stream_name, expected_first_logger_info_data),
                    call(self.stream_name, expected_second_logger_info_data)
                ]
            )

    def test_splunk_logging_missing_data(self):
        """Tests missing key values in the body of the event"""

        with (  # noqa: E999
            patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
            with self.assertRaises(Exception):
                lambda_handler(event={"Records": [{"body": json.dumps([{"": "456"}])}]}, context={})

            expected_first_logger_info_data = {**InvalidValues.logging_with_no_values}

            expected_first_logger_error_data = self.expected_lambda_handler_logs(
                success=False, number_of_rows=1, ingestion_complete=False,
                diagnostics="'NoneType' object has no attribute 'replace'"
            )

            first_logger_info_call_args = json.loads(self.extract_all_call_args_for_logger_info(mock_logger)[0])
            first_logger_error_call_args = json.loads(self.extract_all_call_args_for_logger_error(mock_logger)[0])
            self.assertEqual(first_logger_info_call_args, expected_first_logger_info_data)
            self.assertEqual(first_logger_error_call_args, expected_first_logger_error_data)

            self.assertEqual(
                mock_send_log_to_firehose.call_args_list, [
                    call(self.stream_name, expected_first_logger_info_data),
                    call(self.stream_name, expected_first_logger_error_data)
                ],
            )

    @patch("common.log_decorator.send_log_to_firehose")
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
            with (  # noqa: E999
                patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
                patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
            ):  # noqa: E999
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
                [
                    call(self.stream_name, expected_first_logger_info_data),
                    call(self.stream_name, expected_second_logger_info_data)
                ]
            )

    def test_splunk_logging_multiple_rows(self):
        """Tests logging for multiple objects in the body of the event"""
        messages = [{"row_id": "test1"}, {"row_id": "test2"}]

        with (  # noqa: E999
            patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
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
                call(self.stream_name, expected_first_logger_info_data),
                call(self.stream_name, expected_second_logger_info_data),
                call(self.stream_name, expected_third_logger_info_data),
            ]
        )

    @patch("common.log_decorator.send_log_to_firehose")
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

        with (  # noqa: E999
            patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
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
                call(self.stream_name, expected_first_logger_info_data),
                call(self.stream_name, expected_second_logger_info_data),
                call(self.stream_name, expected_third_logger_info_data),
                call(self.stream_name, expected_fourth_logger_info_data),
            ]
        )

    def test_splunk_update_ack_file_not_logged(self):
        self.maxDiff = None
        """Tests that update_ack_file is not logged if we have sent acks for less than the whole file"""
        # send 98 messages
        messages = []
        for i in range(1, 99):
            message_value = "test" + str(i)
            messages.append({"row_id": message_value})

        with (  # noqa: E999
            patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
            patch("update_ack_file.change_audit_table_status_to_processed")
                as mock_change_audit_table_status_to_processed,  # noqa: E999
        ):  # noqa: E999
            result = lambda_handler(generate_event(messages), context={})

        self.assertEqual(result, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)

        expected_secondlast_logger_info_data = {
                **ValidValues.mock_message_expected_log_value,
                "message_id": "test98",
            }
        expected_last_logger_info_data = self.expected_lambda_handler_logs(success=True, number_of_rows=98)

        all_logger_info_call_args = self.extract_all_call_args_for_logger_info(mock_logger)
        secondlast_logger_info_call_args = json.loads(all_logger_info_call_args[97])
        last_logger_info_call_args = json.loads(all_logger_info_call_args[98])

        self.assertEqual(secondlast_logger_info_call_args, expected_secondlast_logger_info_data)
        self.assertEqual(last_logger_info_call_args, expected_last_logger_info_data)

        mock_send_log_to_firehose.assert_has_calls(
            [
                call(self.stream_name, secondlast_logger_info_call_args),
                call(self.stream_name, last_logger_info_call_args),
            ]
        )
        mock_change_audit_table_status_to_processed.assert_not_called()

    def test_splunk_update_ack_file_logged(self):
        """Tests that update_ack_file is logged if we have sent acks for the whole file"""
        # send 99 messages
        messages = []
        for i in range(1, 100):
            message_value = "test" + str(i)
            messages.append({"row_id": message_value})

        with (  # noqa: E999
            patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("common.log_decorator.logger") as mock_logger,  # noqa: E999
            patch("update_ack_file.change_audit_table_status_to_processed")
                as mock_change_audit_table_status_to_processed,  # noqa: E999
        ):  # noqa: E999
            result = lambda_handler(generate_event(messages), context={})

        self.assertEqual(result, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)

        expected_thirdlast_logger_info_data = {
                **ValidValues.mock_message_expected_log_value,
                "message_id": "test99",
            }
        expected_secondlast_logger_info_data = {
                **ValidValues.upload_ack_file_expected_log,
                "message_id": "test1",
                "time_taken": "1.0s"
            }
        expected_last_logger_info_data = self.expected_lambda_handler_logs(
            success=True, number_of_rows=99, ingestion_complete=True
        )

        all_logger_info_call_args = self.extract_all_call_args_for_logger_info(mock_logger)
        thirdlast_logger_info_call_args = json.loads(all_logger_info_call_args[98])
        secondlast_logger_info_call_args = json.loads(all_logger_info_call_args[99])
        last_logger_info_call_args = json.loads(all_logger_info_call_args[100])
        self.assertEqual(thirdlast_logger_info_call_args, expected_thirdlast_logger_info_data)
        self.assertEqual(secondlast_logger_info_call_args, expected_secondlast_logger_info_data)
        self.assertEqual(last_logger_info_call_args, expected_last_logger_info_data)

        mock_send_log_to_firehose.assert_has_calls(
            [
                call(self.stream_name, thirdlast_logger_info_call_args),
                call(self.stream_name, secondlast_logger_info_call_args),
                call(self.stream_name, last_logger_info_call_args),
            ]
        )
        mock_change_audit_table_status_to_processed.assert_called()


if __name__ == "__main__":
    unittest.main()
