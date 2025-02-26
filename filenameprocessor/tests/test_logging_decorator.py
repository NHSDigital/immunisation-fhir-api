"""Tests for the logging_decorator and its helper functions"""

import unittest
from unittest.mock import patch
import json
from copy import deepcopy
from contextlib import ExitStack
from boto3 import client as boto3_client
from moto import mock_s3, mock_firehose, mock_sqs, mock_dynamodb

from tests.utils_for_tests.generic_setup_and_teardown import GenericSetUp, GenericTearDown
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames, Firehose
from tests.utils_for_tests.values_for_tests import MockFileDetails, fixed_datetime
from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from clients import REGION_NAME
    from file_name_processor import lambda_handler
    from logging_decorator import send_log_to_firehose, generate_and_send_logs
    from constants import PERMISSIONS_CONFIG_FILE_KEY

s3_client = boto3_client("s3", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

FILE_DETAILS = MockFileDetails.emis_flu
MOCK_VACCINATION_EVENT = {
    "Records": [{"s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": FILE_DETAILS.file_key}}}]
}
MOCK_CONFIG_EVENT = {
    "Records": [{"s3": {"bucket": {"name": BucketNames.CONFIG}, "object": {"key": PERMISSIONS_CONFIG_FILE_KEY}}}]
}


@mock_s3
@mock_firehose
@mock_sqs
@mock_dynamodb
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestLoggingDecorator(unittest.TestCase):
    """Tests for the logging_decorator and its helper functions"""

    def setUp(self):
        """Set up the mock AWS environment and upload a valid FLU/EMIS file example"""
        GenericSetUp(s3_client, firehose_client, sqs_client, dynamodb_client)
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=FILE_DETAILS.file_key)

    def tearDown(self):
        """Clean the mock AWS environment"""
        GenericTearDown(s3_client, firehose_client, sqs_client, dynamodb_client)

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
            patch("audit_table.logger"),
            patch("file_name_processor.logger"),
            patch("send_sqs_message.logger"),
            patch("supplier_permissions.logger"),
            patch("utils_for_filenameprocessor.logger"),
            # Time is incremented by 1.0 for each call to time.time for ease of testing.
            # Range is set to a large number (100) due to many calls being made to time.time for some tests.
            patch("logging_decorator.time.time", side_effect=[0.0 + i for i in range(100)]),
        ]

        # Set up the ExitStack. Note that patches need to be explicitly started so that they will be applied even when
        # only running one individual test.
        with ExitStack() as stack:
            # datetime.now is patched to return a fixed datetime for ease of testing
            mock_datetime = patch("logging_decorator.datetime").start()
            mock_datetime.now.return_value = fixed_datetime
            stack.enter_context(patch("logging_decorator.datetime", mock_datetime))

            for common_patch in common_patches:
                common_patch.start()
                stack.enter_context(common_patch)

            super().run(result)

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

    def test_logging_successful_validation(self):
        """Tests that the correct logs are sent to cloudwatch and splunk when file validation is successful"""
        # Mock full permissions so that validation will pass
        permissions_config_content = generate_permissions_config_content(deepcopy(FILE_DETAILS.permissions_config))
        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=FILE_DETAILS.message_id),  # noqa: E999
            patch("elasticache.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(MOCK_VACCINATION_EVENT, context=None)

        expected_log_data = {
            "function_name": "filename_processor_handle_record",
            "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "time_taken": "1.0s",
            "statusCode": 200,
            "message": "Successfully sent to SQS for further processing",
            "file_key": FILE_DETAILS.file_key,
            "message_id": FILE_DETAILS.message_id,
            "vaccine_type": FILE_DETAILS.vaccine_type,
            "supplier": FILE_DETAILS.supplier,
        }

        log_data = json.loads(mock_logger.info.call_args[0][0])
        self.assertEqual(log_data, expected_log_data)

        mock_send_log_to_firehose.assert_called_once_with(log_data)

    def test_logging_failed_validation(self):
        """Tests that the correct logs are sent to cloudwatch and splunk when file validation fails"""
        # Set up permissions for COVID19 only (file is for FLU), so that validation will fail
        permissions_config_content = generate_permissions_config_content({"EMIS": ["COVID19_FULL"]})

        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=FILE_DETAILS.message_id),  # noqa: E999
            patch("elasticache.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(MOCK_VACCINATION_EVENT, context=None)

        expected_log_data = {
            "function_name": "filename_processor_handle_record",
            "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "time_taken": "1.0s",
            "statusCode": 403,
            "message": "Infrastructure Level Response Value - Processing Error",
            "file_key": FILE_DETAILS.file_key,
            "message_id": FILE_DETAILS.message_id,
            "error": "Initial file validation failed: EMIS does not have permissions for FLU",
        }

        log_data = json.loads(mock_logger.info.call_args[0][0])
        self.assertEqual(log_data, expected_log_data)

        mock_send_log_to_firehose.assert_called_once_with(log_data)

    def test_logging_successful_config_upload(self):
        """
        Tests that the correct logs are sent to cloudwatch and splunk when the config cache is successfully updated
        """
        # Create a permissions config file and upload it to the config bucket
        permissions_config_content = generate_permissions_config_content(deepcopy(FILE_DETAILS.permissions_config))
        s3_client.put_object(
            Bucket=BucketNames.CONFIG, Key=PERMISSIONS_CONFIG_FILE_KEY, Body=permissions_config_content
        )

        with (  # noqa: E999
            patch("elasticache.redis_client.set"),  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(MOCK_CONFIG_EVENT, context=None)

        expected_log_data = {
            "function_name": "filename_processor_handle_record",
            "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "time_taken": "1.0s",
            "statusCode": 200,
            "message": "File content successfully uploaded to cache",
            "file_key": PERMISSIONS_CONFIG_FILE_KEY,
        }

        log_data = json.loads(mock_logger.info.call_args[0][0])
        self.assertEqual(log_data, expected_log_data)

        mock_send_log_to_firehose.assert_called_once_with(log_data)
