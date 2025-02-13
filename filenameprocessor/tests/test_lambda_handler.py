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
from tests.utils_for_tests.utils_for_filenameprocessor_tests import (
    generate_permissions_config_content,
    generate_dict_full_permissions_all_suppliers_and_vaccine_types,
    add_entry_to_table,
    assert_audit_table_entry,
)
from tests.utils_for_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames, Sqs
from tests.utils_for_tests.values_for_tests import MOCK_CREATED_AT_FORMATTED_STRING, MockFileDetails

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from file_name_processor import lambda_handler
    from clients import REGION_NAME
    from constants import PERMISSIONS_CONFIG_FILE_KEY, AUDIT_TABLE_NAME, FileStatus, AuditTableKeys


s3_client = boto3_client("s3", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

# NOTE: The default throughout these tests is to use permissions config which allows all suppliers full permissions
# for all vaccine types. This default is overridden for some specific tests.
all_vaccine_types_in_this_test_file = ["RSV", "FLU"]
all_suppliers_in_this_test_file = ["RAVS", "EMIS"]
all_permissions_config_content = generate_permissions_config_content(
    generate_dict_full_permissions_all_suppliers_and_vaccine_types(
        all_suppliers_in_this_test_file, all_vaccine_types_in_this_test_file
    )
)


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
            # Patch the permissions config to allow all suppliers full permissions for all vaccine types.
            patch("elasticache.redis_client.get", return_value=all_permissions_config_content),
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
    def make_event_with_message_id(file_key: str, message_id: str):
        """Makes an event with s3 bucket name set to BucketNames.SOURCE and and s3 object key set to the file_key."""
        return {
            "Records": [
                {"s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": file_key}}, "message_id": message_id}
            ]
        }

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

    def assert_ack_file_contents(self, file_details: MockFileDetails) -> None:
        """Assert that the ack file if given, else the VALID_FLU_EMIS_ACK_FILE_KEY, is in the destination S3 bucket"""
        retrieved_object = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=file_details.ack_file_key)
        actual_ack_content = retrieved_object["Body"].read().decode("utf-8")
        expected_ack_content = self.generate_expected_failure_inf_ack_content(
            file_details.message_id, file_details.created_at_formatted_string
        )
        self.assertEqual(actual_ack_content, expected_ack_content)

    def assert_no_ack_file(self, file_details: MockFileDetails) -> None:
        """Assert that there is no ack file created for the given file"""
        with self.assertRaises(s3_client.exceptions.NoSuchKey):
            s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=file_details.ack_file_key)

    def assert_no_sqs_message(self) -> None:
        """Assert that there are no messages in the SQS queue"""
        messages = sqs_client.receive_message(QueueUrl=Sqs.TEST_QUEUE_URL, MaxNumberOfMessages=10)
        self.assertEqual(messages.get("Messages", []), [])

    def assert_not_in_audit_table(self, file_details: MockFileDetails) -> None:
        """Assert that the file is not in the audit table"""
        table_entry = dynamodb_client.get_item(
            TableName=AUDIT_TABLE_NAME, Key={AuditTableKeys.MESSAGE_ID: {"S": file_details.message_id}}
        ).get("Item")
        self.assertIsNone(table_entry)

    def assert_sqs_message(self, file_details: MockFileDetails) -> None:
        """Assert that the correct message is in the SQS queue"""
        messages = sqs_client.receive_message(QueueUrl=Sqs.TEST_QUEUE_URL, MaxNumberOfMessages=10)
        received_messages = messages.get("Messages", [])
        self.assertEqual(len(received_messages), 1)
        expected_sqs_message = {
            **file_details.sqs_message_body,
            "permission": [f"{vaccine_type.upper()}_FULL" for vaccine_type in all_vaccine_types_in_this_test_file],
        }
        self.assertEqual(json_loads(received_messages[0]["Body"]), expected_sqs_message)

    @staticmethod
    def get_audit_table_items():
        """Return all items in the audit table"""
        return dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

    def test_lambda_handler_new_file_success_and_first_in_queue(self):
        """
        Tests that for a new file, which passes validation and is the only file processing for the supplier_vaccineType
        queue:
        * The file is added to the audit table with a status of 'processing'
        * The message is sent to SQS
        * The make_and_upload_the_ack_file method is not called
        * The invoke_filename_lambda method is not called
        """
        # NOTE: Add a test case for each vaccine type
        test_cases = [MockFileDetails.emis_flu, MockFileDetails.ravs_rsv_1]
        for file_details in test_cases:
            with self.subTest(file_details.name):
                # Setup the file in the source bucket
                s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

                with (
                    patch("file_name_processor.uuid4", return_value=file_details.message_id),
                    patch("file_name_processor.invoke_filename_lambda") as mock_invoke_filename_lambda,
                ):
                    lambda_handler(self.make_event(file_details.file_key), None)

                assert_audit_table_entry(file_details, FileStatus.PROCESSING)
                self.assert_sqs_message(file_details)
                mock_invoke_filename_lambda.assert_not_called()
                self.assert_no_ack_file(file_details)

                # Reset audit table
                for item in self.get_audit_table_items():
                    dynamodb_client.delete_item(TableName=AUDIT_TABLE_NAME, Key=dict(item.items()))

    def test_lambda_handler_failure(self):
        """ "
        # 1. New file fails validation. - nothing in queue
        # New file fails permissions - something in queue
        #2. Duplicate file. - something in queue
        # 3. New file passes validation, and no files ahead in the queue.
        4. New file passes validation, and files ahead in the queue.
        5. Existing file passes validation.
        6. Existing file fails validation.
        #7. File not in root
        """

    def test_lambda_handler_existing_file_success(self):
        """
        Tests that for an existing file, which passes validation and is the only file processing for the
        supplier_vaccineType queue:
        * The file status is updated to 'processing' in the audit table
        * The message is sent to SQS
        * The make_and_upload_the_ack_file method is not called
        * The invoke_filename_lambda method is not called
        """
        file_details = MockFileDetails.ravs_rsv_1
        add_entry_to_table(file_details, FileStatus.QUEUED)

        with (
            patch("file_name_processor.uuid4", return_value=file_details.message_id),
            patch("file_name_processor.invoke_filename_lambda") as mock_invoke_filename_lambda,
        ):
            lambda_handler(self.make_event_with_message_id(file_details.file_key, file_details.message_id), None)

        assert_audit_table_entry(file_details, FileStatus.PROCESSING)
        self.assert_sqs_message(file_details)
        self.assert_no_ack_file(file_details)
        mock_invoke_filename_lambda.assert_not_called()

    def test_lambda_handler_non_root_file(self):
        """
        Tests that when the file is not in the root of the source bucket, no action is taken:
        * The file is not added to the audit table
        * The message is not sent to SQS
        * The failure inf_ack file is not created
        * The invoke_filename_lambda method is not called
        """
        file_details = MockFileDetails.emis_flu
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key="folder/" + file_details.file_key)

        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
            patch("file_name_processor.invoke_filename_lambda") as mock_invoke_filename_lambda,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event("folder/" + file_details.file_key), context=None)

        self.assert_not_in_audit_table(file_details)
        self.assert_no_sqs_message()
        self.assert_no_ack_file(file_details)
        mock_invoke_filename_lambda.assert_not_called()

    def test_lambda_handler_duplicate_file_other_files_in_queue(self):
        """
        Tests that for a file that is a duplicate of a file, and there are other files in the same supplier_vaccineType
        queue:
        * The file is added to the audit table with a status of 'Duplicate'
        * The message is not sent to SQS
        * The failure inf_ack file is created
        * The invoke_filename_lambda method is not called
        """
        file_details = MockFileDetails.ravs_rsv_1
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

        duplicate_already_in_table = deepcopy(file_details)
        duplicate_already_in_table.message_id = "duplicate_id"
        duplicate_already_in_table.audit_table_entry[AuditTableKeys.MESSAGE_ID] = {
            "S": duplicate_already_in_table.message_id
        }
        add_entry_to_table(duplicate_already_in_table, FileStatus.PROCESSED)

        queued_file_details = MockFileDetails.ravs_rsv_2
        add_entry_to_table(queued_file_details, FileStatus.QUEUED)

        with (
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
            patch("file_name_processor.invoke_filename_lambda") as mock_invoke_filename_lambda,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event(file_details.file_key), context=None)

        assert_audit_table_entry(file_details, FileStatus.DUPLICATE)
        self.assert_no_sqs_message()
        self.assert_ack_file_contents(file_details)
        mock_invoke_filename_lambda.assert_called_with(queued_file_details.file_key, queued_file_details.message_id)

    def test_lambda_invalid_file_key_no_other_files_in_queue(self):
        """
        Tests that when the file_key is invalid, and there are no other files in the supplier_vaccineType queue:
        * The file is added to the audit table with a status of 'Processed'
        * The message is not sent to SQS
        * The failure inf_ack file is created
        * The invoke_filename_lambda method is not called
        """
        invalid_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=invalid_file_key)
        file_details = deepcopy(MockFileDetails.ravs_rsv_1)
        file_details.file_key = invalid_file_key
        file_details.ack_file_key = self.get_ack_file_key(invalid_file_key)

        with (  # noqa: E999
            patch(  # noqa: E999
                "file_name_processor.validate_vaccine_type_permissions"  # noqa: E999
            ) as mock_validate_vaccine_type_permissions,  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
            patch("file_name_processor.invoke_filename_lambda") as mock_invoke_filename_lambda,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event(invalid_file_key), context=None)

        expected_table_items = [
            {
                "message_id": {"S": file_details.message_id},
                "filename": {"S": file_details.file_key},
                "queue_name": {"S": "unknown_unknown"},
                "status": {"S": "Processed"},
                "timestamp": {"S": file_details.created_at_formatted_string},
            }
        ]
        self.assertEqual(self.get_audit_table_items(), expected_table_items)
        mock_validate_vaccine_type_permissions.assert_not_called()
        self.assert_ack_file_contents(file_details)
        mock_invoke_filename_lambda.assert_not_called()
        self.assert_no_sqs_message()

    def test_lambda_invalid_permissions(self):
        """Tests that SQS queue is not called when supplier has no permissions for the vaccine type"""
        file_details = MockFileDetails.emis_flu
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_details.file_key)

        # Mock the supplier permissions with a value which doesn't include the requested Flu permissions
        permissions_config_content = generate_permissions_config_content({"EMIS": ["RSV_DELETE"]})
        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
            patch("elasticache.redis_client.get", return_value=permissions_config_content),  # noqa: E999
            patch("send_sqs_message.send_to_supplier_queue") as mock_send_to_supplier_queue,  # noqa: E999
        ):  # noqa: E999
            lambda_handler(event=self.make_event(file_details.file_key), context=None)

        expected_table_items = [{**file_details.audit_table_entry, "status": {"S": "Processed"}}]
        self.assertEqual(self.get_audit_table_items(), expected_table_items)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_contents(file_details)


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
