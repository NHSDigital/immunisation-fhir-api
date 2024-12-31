"""Tests for the logging_decorator and its helper functions"""

import unittest
from unittest.mock import patch
import json
from copy import deepcopy
from boto3 import client as boto3_client
from moto import mock_s3
from file_name_processor import lambda_handler
from clients import REGION_NAME
from tests.utils_for_tests.values_for_tests import MOCK_ENVIRONMENT_DICT, MockFileDetails, BucketNames
from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content


s3_client = boto3_client("s3", region_name=REGION_NAME)
FILE_DETAILS = MockFileDetails.flu_emis
MOCK_EVENT = {"Records": [{"s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": FILE_DETAILS.file_key}}}]}


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestLoggingDecorator(unittest.TestCase):
    """Tests for the logging_decorator and its helper functions"""

    def setUp(self):
        """Set up the S3 buckets and upload the valid FLU/EMIS file example"""
        for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME})

        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=FILE_DETAILS.file_key)

    def test_splunk_logger_successful_validation(self):
        """Tests the splunk logger is called when file validation is successful"""
        # Mock full permissions so that validation will pass
        permissions_config_content = generate_permissions_config_content(deepcopy(FILE_DETAILS.permissions_config))
        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=FILE_DETAILS.message_id),  # noqa: E999
            patch("send_sqs_message.send_to_supplier_queue"),  # noqa: E999
            patch("file_name_processor.add_to_audit_table"),  # noqa: E999
            patch("supplier_permissions.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(MOCK_EVENT, context=None)

        expected_log_data = {
            "function_name": "filename_processor_handle_record",
            "date_time": "REPLACE THIS VALUE",
            "time_taken": "REPLACE THIS VALUE",
            "statusCode": 200,
            "message": "Successfully sent to SQS queue",
            "file_key": FILE_DETAILS.file_key,
            "message_id": FILE_DETAILS.message_id,
            "vaccine_type": FILE_DETAILS.vaccine_type,
            "supplier": FILE_DETAILS.supplier,
        }

        log_data = json.loads(mock_logger.info.call_args[0][0])
        expected_log_data["time_taken"] = log_data["time_taken"]
        expected_log_data["date_time"] = log_data["date_time"]
        self.assertEqual(log_data, expected_log_data)

        mock_send_log_to_firehose.assert_called_once_with(log_data)

    def test_splunk_logger_failed_validation(self):
        """Tests the splunk logger is called when file validation is unsuccessful"""
        # Set up permissions for COVID19 only (file is for FLU), so that validation will fail
        permissions_config_content = generate_permissions_config_content({"EMIS": ["COVID19_FULL"]})

        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=FILE_DETAILS.message_id),  # noqa: E999
            patch("file_name_processor.add_to_audit_table"),  # noqa: E999
            patch("supplier_permissions.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("send_sqs_message.send_to_supplier_queue"),  # noqa: E999
            patch("logging_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.logger") as mock_logger,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(MOCK_EVENT, context=None)

        expected_log_data = {
            "function_name": "filename_processor_handle_record",
            "date_time": "REPLACE THIS VALUE",
            "time_taken": "REPLACE THIS VALUE",
            "statusCode": 403,
            "message": "Infrastructure Level Response Value - Processing Error",
            "file_key": FILE_DETAILS.file_key,
            "message_id": FILE_DETAILS.message_id,
            "error": "Initial file validation failed: EMIS does not have permissions for FLU",
        }

        log_data = json.loads(mock_logger.info.call_args[0][0])
        expected_log_data["time_taken"] = log_data["time_taken"]
        expected_log_data["date_time"] = log_data["date_time"]
        self.assertEqual(log_data, expected_log_data)

        mock_send_log_to_firehose.assert_called_once_with(log_data)
