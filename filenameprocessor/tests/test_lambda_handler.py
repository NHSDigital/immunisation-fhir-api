"""Tests for lambda_handler"""

from unittest.mock import patch
from unittest import TestCase
from json import loads as json_loads
from contextlib import ExitStack
from copy import deepcopy
import fakeredis
from boto3 import client as boto3_client
from moto import mock_s3, mock_sqs, mock_firehose, mock_dynamodb

from tests.utils_for_tests.generic_setup_and_teardown import GenericSetUp, GenericTearDown
from tests.utils_for_tests.utils_for_filenameprocessor_tests import generate_permissions_config_content
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames, Sqs
from tests.utils_for_tests.values_for_tests import MOCK_CREATED_AT_FORMATTED_STRING, MockFileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from file_name_processor import lambda_handler
    from clients import REGION_NAME
    from constants import PERMISSIONS_CONFIG_FILE_KEY
    from audit_table import AUDIT_TABLE_NAME


s3_client = boto3_client("s3", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_sqs
@mock_firehose
@mock_dynamodb
class TestLambdaHandlerDataSource(TestCase):
    """Tests for lambda_handler when a data sources (vaccine data) file is received."""

    def run(self, result=None):
        """
        This method is run by Unittest, and is being utilised here to apply common patches to all of the tests in the
        class. Using ExitStack allows multiple patches to be applied, whilst ensuring that the mocks are cleaned up
        after the test has run.
        """
        # Set up common patches to be applied to all tests in the class (these can be overridden in individual tests.)
        common_patches = [
            # Patch get_created_at_formatted_string, so that the ack file key can be deduced
            # (it is already unittested separately).
            patch("file_name_processor.get_created_at_formatted_string", return_value=MOCK_CREATED_AT_FORMATTED_STRING),
            # Patch redis_client to use a fake redis client.
            patch("elasticache.redis_client", new=fakeredis.FakeStrictRedis()),
        ]

        with ExitStack() as stack:
            for common_patch in common_patches:
                stack.enter_context(common_patch)
            super().run(result)

    def setUp(self):
        GenericSetUp(s3_client, firehose_client, sqs_client, dynamodb_client)

    def tearDown(self):
        GenericTearDown(s3_client, firehose_client, sqs_client, dynamodb_client)

    @staticmethod
    def make_event(file_key: str):
        """Makes an event with s3 bucket name set to BucketNames.SOURCE and and s3 object key set to the file_key."""
        return {"Records": [{"s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": file_key}}}]}

    @staticmethod
    def get_ack_file_key(file_key: str) -> str:
        """Returns the ack file key for the given file key"""
        return f"ack/{file_key.replace('.csv', '_InfAck_' + MOCK_CREATED_AT_FORMATTED_STRING + '.csv')}"

    @staticmethod
    def generate_expected_failure_inf_ack_content(message_id: str, created_at_formatted_string: str) -> str:
        """Create an ack row, containing the given message details."""
        return (
            "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
            + "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|MESSAGE_DELIVERY\r\n"
            + f"{message_id}|Failure|Fatal|Fatal Error|10001|Technical|10002|"
            + f"Infrastructure Level Response Value - Processing Error|{created_at_formatted_string}|||False\r\n"
        )

    def assert_ack_file_contents(self, ack_file_key: str, message_id: str, created_at_formatted_string: str) -> None:
        """Assert that the ack file if given, else the VALID_FLU_EMIS_ACK_FILE_KEY, is in the destination S3 bucket"""
        retrieved_object = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=ack_file_key)
        actual_ack_content = retrieved_object["Body"].read().decode("utf-8")
        expected_ack_content = self.generate_expected_failure_inf_ack_content(message_id, created_at_formatted_string)
        self.assertEqual(actual_ack_content, expected_ack_content)

    @staticmethod
    def get_table_items():
        """Return all items in the audit table"""
        return dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

    def test_lambda_handler_success(self):
        """Tests that lambda handler runs successfully for files with valid file keys and permissions."""
        # NOTE: Add a test case for each vaccine type
        test_cases = [MockFileDetails.flu_emis, MockFileDetails.rsv_ravs]
        for file_details in test_cases:
            with self.subTest(file_details.name):
                # Setup the file in the source bucket
                s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

                # Mock full permissions for the supplier for the vaccine type, and the message_id as the file_details
                # message_id
                permissions_config_content = generate_permissions_config_content(
                    deepcopy(file_details.permissions_config)
                )
                with (
                    patch("elasticache.redis_client.get", return_value=permissions_config_content),
                    patch("file_name_processor.uuid4", return_value=file_details.message_id),
                ):
                    lambda_handler(self.make_event(file_details.file_key), None)

                # Check if file was successfully added to the audit table
                table_items = self.get_table_items()
                self.assertEqual(len(table_items), 1)
                expected_table_item = {
                    "message_id": {"S": file_details.message_id},
                    "filename": {"S": file_details.file_key},
                    "queue_name": {"S": file_details.queue_name},
                    "status": {"S": "Processing"},
                    "timestamp": {"S": file_details.created_at_formatted_string},
                }
                self.assertEqual(table_items[0], expected_table_item)

                # Check if the message was sent to the SQS queue
                messages = sqs_client.receive_message(QueueUrl=Sqs.TEST_QUEUE_URL, MaxNumberOfMessages=10)
                received_messages = messages.get("Messages", [])
                self.assertEqual(len(received_messages), 1)
                self.assertEqual(json_loads(received_messages[0]["Body"]), file_details.sqs_message_body)

                # Reset audit table
                for item in self.get_table_items():
                    dynamodb_client.delete_item(TableName=AUDIT_TABLE_NAME, Key=dict(item.items()))

    def test_lambda_invalid_file_key(self):
        """tests SQS queue is not called when file key includes invalid file key"""
        test_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=test_file_key)

        with (  # noqa: E999
            patch(  # noqa: E999
                "file_name_processor.validate_vaccine_type_permissions"  # noqa: E999
            ) as mock_validate_vaccine_type_permissions,  # noqa: E999
            patch("file_name_processor.uuid4", return_value="test_id"),  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event(test_file_key), context=None)

        table_items = self.get_table_items()
        self.assertEqual(len(table_items), 1)
        expected_table_item = {
            "message_id": {"S": "test_id"},
            "filename": {"S": test_file_key},
            "queue_name": {"S": "unknown_unknown"},
            "status": {"S": "Processed"},
            "timestamp": {"S": MOCK_CREATED_AT_FORMATTED_STRING},
        }
        self.assertEqual(table_items[0], expected_table_item)

        mock_validate_vaccine_type_permissions.assert_not_called()
        self.assert_ack_file_contents(
            ack_file_key=self.get_ack_file_key(test_file_key),
            message_id="test_id",
            created_at_formatted_string=MOCK_CREATED_AT_FORMATTED_STRING,
        )

    def test_lambda_invalid_permissions(self):
        """Tests that SQS queue is not called when supplier has no permissions for the vaccine type"""
        file_details = MockFileDetails.flu_emis
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

        # Mock the supplier permissions with a value which doesn't include the requested Flu permissions
        permissions_config_content = generate_permissions_config_content({"EMIS": ["RSV_DELETE"]})
        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
            patch("elasticache.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("send_sqs_message.send_to_supplier_queue") as mock_send_to_supplier_queue,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event(file_details.file_key), context=None)

        table_items = self.get_table_items()
        self.assertEqual(len(table_items), 1)
        expected_table_item = {
            "message_id": {"S": file_details.message_id},
            "filename": {"S": file_details.file_key},
            "queue_name": {"S": file_details.queue_name},
            "status": {"S": "Processed"},
            "timestamp": {"S": file_details.created_at_formatted_string},
        }
        self.assertEqual(table_items[0], expected_table_item)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_contents(
            ack_file_key=self.get_ack_file_key(file_details.file_key),
            message_id=file_details.message_id,
            created_at_formatted_string=file_details.created_at_formatted_string,
        )


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_firehose
class TestLambdaHandlerConfig(TestCase):
    """Tests for lambda_handler when a config file is uploaded."""

    config_event = {
        "Records": [{"s3": {"bucket": {"name": BucketNames.CONFIG}, "object": {"key": (PERMISSIONS_CONFIG_FILE_KEY)}}}]
    }

    mock_permissions_config = generate_permissions_config_content(
        {"test_supplier_1": ["RSV_FULL"], "test_supplier_2": ["FLU_CREATE", "FLU_UPDATE"]}
    )

    def setUp(self):
        GenericSetUp(s3_client, firehose_client)

        s3_client.put_object(
            Bucket=BucketNames.CONFIG, Key=PERMISSIONS_CONFIG_FILE_KEY, Body=self.mock_permissions_config
        )

    def tearDown(self):
        GenericTearDown(s3_client, firehose_client)

    def test_successful_processing_from_configs(self):
        """Tests that the permissions config file content is uploaded to elasticache successfully"""
        with patch("elasticache.redis_client", new=fakeredis.FakeStrictRedis()) as fake_redis:
            lambda_handler(self.config_event, None)

        self.assertEqual(
            json_loads(fake_redis.get(PERMISSIONS_CONFIG_FILE_KEY)), json_loads(self.mock_permissions_config)
        )
