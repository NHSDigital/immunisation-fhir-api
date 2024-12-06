"""Tests for lambda_handler"""

from unittest.mock import patch
from unittest import TestCase
from io import BytesIO
from json import loads as json_loads
from contextlib import ExitStack
from copy import deepcopy
from boto3 import client as boto3_client
from moto import mock_s3, mock_sqs
from clients import REGION_NAME
from file_name_processor import lambda_handler
from supplier_permissions import PERMISSIONS_CONFIG_FILE_KEY
from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content
from tests.utils_for_tests.values_for_tests import (
    MOCK_ENVIRONMENT_DICT,
    MOCK_CREATED_AT_FORMATTED_STRING,
    BucketNames,
    Sqs,
    MockFileDetails,
)


s3_client = boto3_client("s3", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_sqs
class TestLambdaHandlerDataSource(TestCase):
    """Tests for lambda_handler when a data sources (vaccine data) file is received."""

    def run(self, result=None):
        """
        This method is run by Unittest, and is being utilised here to apply common patches to all of the tests in the
        class. Using ExitStack allows multiple patches to be applied, whilst ensuring that the mocks are cleaned up
        after the test has run.
        """
        # Set up common patches to be applied to all tests in the class.
        # These patches can be overridden in individual tests.
        common_patches = [
            # Patch the created_at_formatted_string, so that the ack file key can be deduced
            # (it is already unittested separately).
            patch("file_name_processor.get_created_at_formatted_string", return_value=MOCK_CREATED_AT_FORMATTED_STRING),
            # Patch add_to_audit_table to prevent it from being called (it is already unittested separately).
            patch("file_name_processor.add_to_audit_table"),
            # Patch the firehose client to prevent it from being called.
            patch("logging_decorator.firehose_client.put_record"),
        ]

        with ExitStack() as stack:
            for common_patch in common_patches:
                stack.enter_context(common_patch)
            super().run(result)

    def setUp(self):
        for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME})

    @staticmethod
    def make_event(file_key: str):
        """Makes an event with s3 bucket name set to BucketNames.SOURCE and and s3 object key set to the file_key."""
        return {"Records": [{"s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": file_key}}}]}

    @staticmethod
    def get_ack_file_key(file_key: str) -> str:
        """Returns the ack file key for the given file key"""
        return f"ack/{file_key.replace('.csv', '_InfAck_' + MOCK_CREATED_AT_FORMATTED_STRING + '.csv')}"

    def assert_ack_file_in_destination_s3_bucket(self, ack_file_key: str):
        """Assert that the ack file if given, else the VALID_FLU_EMIS_ACK_FILE_KEY, is in the destination S3 bucket"""
        objects_in_destination_bucket = s3_client.list_objects_v2(Bucket=BucketNames.DESTINATION)
        object_keys_in_destination_bucket = [obj["Key"] for obj in objects_in_destination_bucket.get("Contents", [])]
        self.assertIn(ack_file_key, object_keys_in_destination_bucket)

    def test_lambda_handler_success(self):
        """Tests that lambda handler runs successfully for files with valid file keys and permissions."""
        queue_url = sqs_client.create_queue(QueueName=Sqs.QUEUE_NAME, Attributes=Sqs.ATTRIBUTES)["QueueUrl"]

        # NOTE: Add a test case for each vaccine type
        test_cases = [MockFileDetails.rsv_ravs, MockFileDetails.flu_emis]
        for file_details in test_cases:
            with self.subTest(file_details.name):
                s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

                # Mock full permissions for the supplier for the vaccine type, and the message_id as the file_details
                # message_id
                permissions_config_content = generate_permissions_config_content(
                    deepcopy(file_details.permissions_config)
                )
                with (  # noqa: E999
                    patch(  # noqa: E999
                        "supplier_permissions.redis_client.get", return_value=permissions_config_content  # noqa: E999
                    ),  # noqa: E999
                    patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
                    patch("file_name_processor.add_to_audit_table") as mock_add_to_audit_table,  # noqa: E999
                ):  # noqa: E999
                    lambda_handler(self.make_event(file_details.file_key), None)

                mock_add_to_audit_table.assert_called_with(
                    file_details.message_id, file_details.file_key, MOCK_CREATED_AT_FORMATTED_STRING
                )

                # Check if the message was sent to the SQS queue
                messages = sqs_client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=1, MaxNumberOfMessages=1)
                self.assertIn("Messages", messages)
                received_message = json_loads(messages["Messages"][0]["Body"])
                self.assertEqual(received_message, file_details.sqs_message_body)

    def test_lambda_invalid_file_key(self):
        """tests SQS queue is not called when file key includes invalid file key"""
        test_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=test_file_key)

        with patch("send_sqs_message.send_to_supplier_queue") as mock_send_to_supplier_queue:  # noqa: E999
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(ack_file_key=self.get_ack_file_key(test_file_key))

    def test_lambda_invalid_permissions(self):
        """Tests that SQS queue is not called when supplier has no permissions for the vaccine type"""
        file_details = MockFileDetails.flu_emis
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

        # Mock the supplier permissions with a value which doesn't include the requested Flu permissions
        permissions_config_content = generate_permissions_config_content({"EMIS": ["RSV_DELETE"]})
        with (  # noqa: E999
            patch("supplier_permissions.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("send_sqs_message.send_to_supplier_queue") as mock_send_to_supplier_queue,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event(file_details.file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(ack_file_key=file_details.ack_file_key)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
class TestLambdaHandlerConfig(TestCase):
    """Tests for lambda_handler when a config file is uploaded."""

    def setUp(self):
        self.mock_config_file_content = BytesIO(b"mock_file_content")
        self.mock_elasticcache_get_object_return_value = {"Body": self.mock_config_file_content}

    config_event = {
        "Records": [{"s3": {"bucket": {"name": BucketNames.CONFIG}, "object": {"key": (PERMISSIONS_CONFIG_FILE_KEY)}}}]
    }

    def test_successful_processing_from_configs(self):
        mock_config_body = self.mock_elasticcache_get_object_return_value

        with (  # noqa: E999
            patch("logging_decorator.send_log_to_firehose"),  # noqa: E999
            patch("elasticcache.redis_client.set") as mock_redis_set,  # noqa: E999
            patch(  # noqa: E999
                "elasticcache.s3_client.get_object", return_value=mock_config_body  # noqa: E999
            ) as mock_s3_get_object,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(self.config_event, None)

        mock_s3_get_object.assert_called_once_with(Bucket=BucketNames.CONFIG, Key=PERMISSIONS_CONFIG_FILE_KEY)
        mock_redis_set.assert_called_once_with(PERMISSIONS_CONFIG_FILE_KEY, "mock_file_content")

    def test_processing_from_configs_failed(self):
        elasticcache_exception = Exception("Simulated ElastiCache upload failure")
        mock_config_body = self.mock_elasticcache_get_object_return_value

        with (  # noqa: E999
            patch("logging_decorator.send_log_to_firehose"),  # noqa: E999
            patch("elasticcache.upload_to_elasticache", side_effect=elasticcache_exception),  # noqa: E999
            patch(  # noqa: E999
                "elasticcache.s3_client.get_object", return_value=mock_config_body  # noqa: E999
            ) as mock_s3_get_object,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(self.config_event, None)

        mock_s3_get_object.assert_called_once_with(Bucket=BucketNames.CONFIG, Key=PERMISSIONS_CONFIG_FILE_KEY)
