"""Tests for the logging_decorator and its helper functions"""

import unittest
from unittest.mock import patch
from datetime import datetime
import json
from copy import deepcopy
from boto3 import client as boto3_client
from moto import mock_s3, mock_firehose
from file_level_validation import file_level_validation
from logging_decorator import send_log_to_firehose, generate_and_send_logs
from clients import REGION_NAME
from errors import InvalidHeaders, NoOperationPermissions
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MOCK_ENVIRONMENT_DICT,
    MockFileDetails,
    BucketNames,
    ValidMockFileContent,
    Firehose,
)
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import GenericSetUp, GenericTearDown

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
MOCK_FILE_DETAILS = MockFileDetails.flu_emis
COMMON_LOG_DATA = {
    "function_name": "record_processor_file_level_validation",
    "date_time": "2024-01-01 12:00:00",  # (tests mock a 2024-01-01 12:00:00 datetime)
    "time_taken": "0.12346s",  # Time taken is rounded to 5 decimal places (tests mock a 0.123456s time taken)
    "file_key": MOCK_FILE_DETAILS.file_key,
    "message_id": MOCK_FILE_DETAILS.message_id,
    "vaccine_type": MOCK_FILE_DETAILS.vaccine_type,
    "supplier": MOCK_FILE_DETAILS.supplier,
}


@mock_s3
@mock_firehose
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestLoggingDecorator(unittest.TestCase):
    """Tests for the logging_decorator and its helper functions"""

    def setUp(self):
        """Set up the S3 buckets and upload the valid FLU/EMIS file example"""
        GenericSetUp(s3_client, firehose_client)

    def tearDown(self):
        GenericTearDown(s3_client, firehose_client)

    def test_send_log_to_firehose(self):
        """
        Tests that the send_log_to_firehose function calls firehose_client.put_record with the correct arguments.
        NOTE: mock_firehose does not persist the data, so at this level it is only possible to test what the call args
        were, not that the data reached the destination.
        """
        log_data = {"test_key": "test_value"}

        with patch("logging_decorator.firehose_client") as mock_firehose_client:
            send_log_to_firehose(log_data)

        expected_firehose_record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        mock_firehose_client.put_record.assert_called_once_with(
            DeliveryStreamName=Firehose.STREAM_NAME, Record=expected_firehose_record
        )

    def test_generate_and_send_logs(self):
        """
        Tests that the generate_and_send_logs function logs the correct data at the correct level for cloudwatch
        and calls send_log_to_firehose with the correct log data
        """
        base_log_data = {"base_key": "base_value"}
        additional_log_data = {"additional_key": "additional_value"}
        start_time = 1672531200

        # CASE: Successful log - is_error_log arg set to False
        with (  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.time") as mock_time,  # noqa: E999
        ):  # noqa: E999
            mock_time.time.return_value = 1672531200.123456  # Mocks the end time to be 0.123456s after the start time
            generate_and_send_logs(start_time, base_log_data, additional_log_data, is_error_log=False)

        expected_log_data = {"base_key": "base_value", "time_taken": "0.12346s", "additional_key": "additional_value"}
        log_data = json.loads(mock_logger.info.call_args[0][0])
        self.assertEqual(log_data, expected_log_data)
        mock_send_log_to_firehose.assert_called_once_with(expected_log_data)

        # CASE: Error log - is_error_log arg set to True
        with (  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.time") as mock_time,  # noqa: E999
        ):  # noqa: E999
            mock_time.time.return_value = 1672531200.123456  # Mocks the end time to be 0.123456s after the start time
            generate_and_send_logs(start_time, base_log_data, additional_log_data, is_error_log=True)

        expected_log_data = {"base_key": "base_value", "time_taken": "0.12346s", "additional_key": "additional_value"}
        log_data = json.loads(mock_logger.error.call_args[0][0])
        self.assertEqual(log_data, expected_log_data)
        mock_send_log_to_firehose.assert_called_once_with(expected_log_data)

    def test_splunk_logger_successful_validation(self):
        """Tests the splunk logger is called when file-level validation is successful"""

        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=MOCK_FILE_DETAILS.file_key,
            Body=ValidMockFileContent.with_new_and_update_and_delete,
        )

        with (  # noqa: E999
            patch("logging_decorator.datetime") as mock_datetime,  # noqa: E999
            patch("logging_decorator.time") as mock_time,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
            patch("logging_decorator.firehose_client") as mock_firehose_client,  # noqa: E999
        ):  # noqa: E999
            mock_time.time.side_effect = [1672531200, 1672531200.123456]
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            file_level_validation(deepcopy(MOCK_FILE_DETAILS.event_full_permissions_dict))

        expected_message = "Successfully sent for record processing"
        expected_log_data = {**COMMON_LOG_DATA, "statusCode": 200, "message": expected_message}

        # Log data is the first positional argument of the first call to logger.info
        log_data = json.loads(mock_logger.info.call_args_list[0][0][0])
        self.assertEqual(log_data, expected_log_data)

        expected_firehose_record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        mock_firehose_client.put_record.assert_called_once_with(
            DeliveryStreamName=Firehose.STREAM_NAME, Record=expected_firehose_record
        )

    def test_splunk_logger_handled_failure(self):
        """Tests the splunk logger is called when file-level validation fails for a known reason"""

        # Test case tuples are structured as (file_content, event_dict, expected_error_type,
        # expected_status_code, expected_error_message)
        test_cases = [
            # CASE: Invalid headers
            (
                ValidMockFileContent.with_new_and_update_and_delete.replace("NHS_NUMBER", "NHS_NUMBERS"),
                MOCK_FILE_DETAILS.event_full_permissions_dict,
                InvalidHeaders,
                400,
                "File headers are invalid.",
            ),
            # CASE: No operation permissions
            (
                ValidMockFileContent.with_new_and_update,
                MOCK_FILE_DETAILS.event_delete_permissions_only_dict,  # No permission for NEW or UPDATE
                NoOperationPermissions,
                403,
                f"{MOCK_FILE_DETAILS.supplier} does not have permissions to perform any of the requested actions.",
            ),
        ]

        for (
            mock_file_content,
            event_dict,
            expected_error_type,
            expected_status_code,
            expected_error_message,
        ) in test_cases:
            with self.subTest(expected_error_message):

                s3_client.put_object(Bucket=BucketNames.SOURCE, Key=MOCK_FILE_DETAILS.file_key, Body=mock_file_content)

                with (  # noqa: E999
                    patch("logging_decorator.datetime") as mock_datetime,  # noqa: E999
                    patch("logging_decorator.time") as mock_time,  # noqa: E999
                    patch("logging_decorator.logger") as mock_logger,  # noqa: E999
                    patch("logging_decorator.firehose_client") as mock_firehose_client,  # noqa: E999
                ):  # noqa: E999
                    mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
                    mock_time.time.side_effect = [1672531200, 1672531200.123456]
                    with self.assertRaises(expected_error_type):
                        file_level_validation(deepcopy(event_dict))

                expected_log_data = {
                    **COMMON_LOG_DATA,
                    "statusCode": expected_status_code,
                    "message": expected_error_message,
                    "error": expected_error_message,
                }

                # Log data is the first positional argument of the first call to logger.error
                log_data = json.loads(mock_logger.error.call_args_list[0][0][0])
                self.assertEqual(log_data, expected_log_data)

                expected_firehose_record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
                mock_firehose_client.put_record.assert_called_once_with(
                    DeliveryStreamName=Firehose.STREAM_NAME, Record=expected_firehose_record
                )

    def test_splunk_logger_unhandled_failure(self):
        """Tests the splunk logger is called when file-level validation fails for an unknown reason"""
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=MOCK_FILE_DETAILS.file_key,
            Body=ValidMockFileContent.with_new_and_update_and_delete,
        )

        with (  # noqa: E999
            patch("logging_decorator.datetime") as mock_datetime,  # noqa: E999
            patch("logging_decorator.time") as mock_time,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
            patch("logging_decorator.firehose_client") as mock_firehose_client,  # noqa: E999
            patch(
                "file_level_validation.validate_content_headers", side_effect=Exception("Test exception")
            ),  # noqa: E999
        ):  # noqa: E999
            mock_time.time.side_effect = [1672531200, 1672531200.123456]
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            with self.assertRaises(Exception):
                file_level_validation(deepcopy(MOCK_FILE_DETAILS.event_full_permissions_dict))

        expected_log_data = {
            **COMMON_LOG_DATA,
            "statusCode": 500,
            "message": "Server error",
            "error": "Test exception",
        }

        # Log data is the first positional argument of the first call to logger.error
        log_data = json.loads(mock_logger.error.call_args_list[0][0][0])
        self.assertEqual(log_data, expected_log_data)

        expected_firehose_record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        mock_firehose_client.put_record.assert_called_once_with(
            DeliveryStreamName=Firehose.STREAM_NAME, Record=expected_firehose_record
        )
