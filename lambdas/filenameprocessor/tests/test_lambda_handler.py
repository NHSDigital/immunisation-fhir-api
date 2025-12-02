"""Tests for lambda_handler"""

import json
import sys
from contextlib import ExitStack
from copy import deepcopy
from json import loads as json_loads
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

import fakeredis
from boto3 import client as boto3_client
from moto import mock_dynamodb, mock_firehose, mock_s3, mock_sqs

from utils_for_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
    Sqs,
)
from utils_for_tests.utils_for_filenameprocessor_tests import (
    MOCK_ODS_CODE_TO_SUPPLIER,
    GenericSetUp,
    GenericTearDown,
    assert_audit_table_entry,
    create_mock_hget,
)
from utils_for_tests.values_for_tests import (
    MOCK_BATCH_FILE_CONTENT,
    MOCK_CREATED_AT_FORMATTED_STRING,
    MOCK_EXPIRES_AT,
    MOCK_EXTENDED_ATTRIBUTES_FILE_CONTENT,
    MockFileDetails,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from constants import (
        AUDIT_TABLE_NAME,
        EXTENDED_ATTRIBUTES_VACC_TYPE,
        AuditTableKeys,
        FileStatus,
    )
    from file_name_processor import handle_record, lambda_handler

s3_client = boto3_client("s3", region_name=REGION_NAME)
sqs_client = boto3_client("sqs", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)

# NOTE: The default throughout these tests is to use permissions config which allows all suppliers full permissions
# for all vaccine types. This default is overridden for some specific tests.
all_vaccine_types_in_this_test_file = ["RSV", "FLU"]
all_suppliers_in_this_test_file = ["RAVS", "EMIS"]
all_permissions_in_this_test_file = [f"{vaccine_type}.CRUDS" for vaccine_type in all_vaccine_types_in_this_test_file]


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
        mock_permissions_map = {
            supplier: json.dumps(all_permissions_in_this_test_file) for supplier in all_suppliers_in_this_test_file
        }
        self.mock_hget = create_mock_hget(MOCK_ODS_CODE_TO_SUPPLIER, mock_permissions_map)

        # Set up common patches to be applied to all tests in the class (these can be overridden in individual tests.)
        common_patches = [
            # Patch get_creation_and_expiry_times, so that the ack file key can be deduced  (it is already unittested
            # separately). Note that files numbered '1', which are predominantly used in these tests, use the
            # MOCK_CREATED_AT_FORMATTED_STRING.
            patch(
                "file_name_processor.get_creation_and_expiry_times",
                return_value=(MOCK_CREATED_AT_FORMATTED_STRING, MOCK_EXPIRES_AT),
            ),
        ]

        with ExitStack() as stack:
            for common_patch in common_patches:
                stack.enter_context(common_patch)
            super().run(result)

    def setUp(self):
        GenericSetUp(s3_client, firehose_client, sqs_client, dynamodb_client)
        self.logger_patcher = patch("file_name_processor.logger")
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        GenericTearDown(s3_client, firehose_client, sqs_client, dynamodb_client)
        self.logger_patcher.stop()

    @staticmethod
    def make_record(file_key: str):
        """Makes a record with s3 bucket name set to BucketNames.SOURCE and and s3 object key set to the file_key."""
        return {"s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": file_key}}}

    @staticmethod
    def make_record_with_message_id(file_key: str, message_id: str):
        """
        Makes a record which includes a message_id, with the s3 bucket name set to BucketNames.SOURCE and
        s3 object key set to the file_key.
        """
        return {
            "s3": {"bucket": {"name": BucketNames.SOURCE}, "object": {"key": file_key}},
            "message_id": message_id,
        }

    def make_event(self, records: list):
        """Makes an event with s3 bucket name set to BucketNames.SOURCE and and s3 object key set to the file_key."""
        return {"Records": records}

    @staticmethod
    def get_ack_file_key(
        file_key: str,
        created_at_formatted_string: str = MOCK_CREATED_AT_FORMATTED_STRING,
    ) -> str:
        """Returns the ack file key for the given file key"""
        return f"ack/{file_key.replace('.csv', '_InfAck_' + created_at_formatted_string + '.csv')}"

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
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": file_details.message_id}},
        ).get("Item")
        self.assertIsNone(table_entry)

    def assert_sqs_message(self, file_details: MockFileDetails) -> None:
        """Assert that the correct message is in the SQS queue"""
        messages = sqs_client.receive_message(QueueUrl=Sqs.TEST_QUEUE_URL, MaxNumberOfMessages=10)
        received_messages = messages.get("Messages", [])
        self.assertEqual(len(received_messages), 1)
        expected_sqs_message = {
            **file_details.sqs_message_body,
            "permission": all_permissions_in_this_test_file,
        }
        self.assertEqual(json_loads(received_messages[0]["Body"]), expected_sqs_message)

    @staticmethod
    def get_audit_table_items():
        """Return all items in the audit table"""
        return dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])

    def test_lambda_handler_no_file_key_throws_exception(self):
        """Tests if exception is thrown when file_key is not provided"""
        broken_record = {"Records": [{"s3": {"bucket": {"name": "test"}}}]}

        lambda_handler(broken_record, None)

        self.mock_logger.error.assert_called_once_with("Error obtaining file_key: %s", ANY)

    @patch("elasticache.get_redis_client")
    def test_lambda_handler_new_file_success_and_first_in_queue(self, mock_get_redis_client):
        """
        Tests that for a new file, which passes validation:
        * The file is added to the audit table with a status of 'processing'
        * The message is sent to SQS
        * The make_and_upload_the_ack_file method is not called
        """
        mock_redis = fakeredis.FakeStrictRedis()
        mock_redis.hget = Mock(side_effect=self.mock_hget)
        mock_redis.hkeys = Mock(return_value=all_vaccine_types_in_this_test_file)
        mock_get_redis_client.return_value = mock_redis

        test_cases = [MockFileDetails.emis_flu, MockFileDetails.ravs_rsv_1]
        for file_details in test_cases:
            with self.subTest(file_details.name):
                # Set up the file in the source bucket
                s3_client.put_object(
                    Bucket=BucketNames.SOURCE,
                    Key=file_details.file_key,
                    Body=MOCK_BATCH_FILE_CONTENT,
                )

                with (  # noqa: E999
                    patch(
                        "file_name_processor.uuid4",
                        return_value=file_details.message_id,
                    ),  # noqa: E999
                ):  # noqa: E999
                    lambda_handler(self.make_event([self.make_record(file_details.file_key)]), None)

                assert_audit_table_entry(file_details, FileStatus.QUEUED)
                self.assert_sqs_message(file_details)
                self.assert_no_ack_file(file_details)

    def test_lambda_handler_non_root_file(self):
        """
        Tests that when the file is not in the root of the source bucket, no action is taken:
        * The file is not added to the audit table
        * The message is not sent to SQS
        * The failure inf_ack file is not created
        """
        file_details = MockFileDetails.emis_flu
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key="folder/" + file_details.file_key)

        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
        ):  # noqa: E999
            lambda_handler(
                self.make_event([self.make_record("folder/" + file_details.file_key)]),
                None,
            )

        self.assert_not_in_audit_table(file_details)
        self.assert_no_sqs_message()
        self.assert_no_ack_file(file_details)

    def test_lambda_handler_extended_attributes_success(self):
        """
        Tests that for an extended attributes file (prefix starts with 'Vaccination_Extended_Attributes'):
        * The file is added to the audit table with a status of 'Processed'
        * The queue_name stored is the extended attribute identifier
        * The file is moved to the destination bucket under archive/
        * No SQS message is sent
        * No ack file is created
        """

        # Build an extended attributes file.
        # FileDetails supports this when vaccine_type starts with 'Vaccination_Extended_Attributes'.
        test_cases = [MockFileDetails.extended_attributes_file]

        # Put file in source bucket
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=test_cases[0].file_key,
            Body=MOCK_EXTENDED_ATTRIBUTES_FILE_CONTENT,
        )

        # TODO: rewrite the bucket patches to use moto

        # Patch uuid4 (message id), and prevent external copy issues by simulating move
        with (
            patch("file_name_processor.uuid4", return_value=test_cases[0].message_id),
            patch(
                "file_name_processor.copy_file_to_external_bucket",
                side_effect=lambda src_bucket, key, dst_bucket, dst_key, exp_owner, exp_src_owner: (
                    s3_client.put_object(
                        Bucket=BucketNames.DESTINATION,
                        Key=dst_key,
                        Body=s3_client.get_object(Bucket=src_bucket, Key=key)["Body"].read(),
                    ),
                ),
            ),
            patch(
                "file_name_processor.delete_file",
                side_effect=lambda src_bucket, key, exp_owner: (
                    s3_client.delete_object(
                        Bucket=BucketNames.SOURCE,
                        Key=key,
                    ),
                ),
            ),
        ):
            lambda_handler(self.make_event([self.make_record(test_cases[0].file_key)]), None)

        # Assert audit table entry captured with Processed and queue_name set to the identifier
        table_items = self.get_audit_table_items()
        self.assertEqual(len(table_items), 1)
        item = table_items[0]
        self.assertEqual(item[AuditTableKeys.MESSAGE_ID]["S"], test_cases[0].message_id)
        self.assertEqual(item[AuditTableKeys.FILENAME]["S"], test_cases[0].file_key)
        self.assertEqual(
            item[AuditTableKeys.QUEUE_NAME]["S"], test_cases[0].ods_code + "_" + EXTENDED_ATTRIBUTES_VACC_TYPE
        )
        self.assertEqual(item[AuditTableKeys.STATUS]["S"], "Processed")
        self.assertEqual(item[AuditTableKeys.TIMESTAMP]["S"], test_cases[0].created_at_formatted_string)
        self.assertEqual(item[AuditTableKeys.EXPIRES_AT]["N"], str(test_cases[0].expires_at))
        # File should be moved to destination/
        dest_key = f"dps_destination/{test_cases[0].file_key}"
        print(f" destination file is at {s3_client.list_objects(Bucket=BucketNames.DESTINATION)}")
        retrieved = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=dest_key)
        self.assertIsNotNone(retrieved)

        # No SQS and no ack file
        self.assert_no_sqs_message()
        self.assert_no_ack_file(test_cases[0])

    # This test won't work until we rewrite it to mock a ClientError on copy.
    # This is because we removed the is_file_in_bucket check.
    '''
    def test_lambda_handler_extended_attributes_failure(self):
        """
        Tests that for an extended attributes file (prefix starts with 'Vaccination_Extended_Attributes'):
        Where the file has not been copied to the destination bucket
        * The file is added to the audit table with a status of 'Failed'
        * The queue_name stored is the extended attribute identifier
        * The file is moved to the archive/ folder in the source bucket
        * No SQS message is sent
        * No ack file is created
        """

        # Build an extended attributes file.
        # FileDetails supports this when vaccine_type starts with 'Vaccination_Extended_Attributes'.
        test_cases = [MockFileDetails.extended_attributes_file]

        # Put file in source bucket
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=test_cases[0].file_key,
            Body=MOCK_EXTENDED_ATTRIBUTES_FILE_CONTENT,
        )

        # TODO: rewrite the bucket patches to use moto

        # Patch uuid4 (message id), and don't move the file
        with (
            patch("file_name_processor.uuid4", return_value=test_cases[0].message_id),
            patch(
                "file_name_processor.copy_file_to_external_bucket",
                side_effect=lambda src_bucket, key, dst_bucket, dst_key, exp_owner, exp_src_owner: (
                    # effectively do nothing
                    None,
                ),
            ),
        ):
            lambda_handler(self.make_event([self.make_record(test_cases[0].file_key)]), None)

        # Assert audit table entry captured with Failed and queue_name set to the identifier.
        # Assert that the ClientError message is a 404 Not Found.
        table_items = self.get_audit_table_items()
        self.assertEqual(len(table_items), 1)
        item = table_items[0]
        self.assertEqual(item[AuditTableKeys.MESSAGE_ID]["S"], test_cases[0].message_id)
        self.assertEqual(item[AuditTableKeys.FILENAME]["S"], test_cases[0].file_key)
        self.assertEqual(
            item[AuditTableKeys.QUEUE_NAME]["S"], test_cases[0].ods_code + "_" + EXTENDED_ATTRIBUTES_VACC_TYPE
        )
        self.assertEqual(item[AuditTableKeys.TIMESTAMP]["S"], test_cases[0].created_at_formatted_string)
        self.assertEqual(item[AuditTableKeys.STATUS]["S"], "Failed")
        self.assertEqual(
            item[AuditTableKeys.ERROR_DETAILS]["S"],
            "An error occurred (404) when calling the HeadObject operation: Not Found",
        )
        self.assertEqual(item[AuditTableKeys.EXPIRES_AT]["N"], str(test_cases[0].expires_at))
        # File should be moved to source under archive/
        dest_key = f"archive/{test_cases[0].file_key}"
        print(f" destination file is at {s3_client.list_objects(Bucket=BucketNames.SOURCE)}")
        retrieved = s3_client.get_object(Bucket=BucketNames.SOURCE, Key=dest_key)
        self.assertIsNotNone(retrieved)

        # No SQS and no ack file
        self.assert_no_sqs_message()
        self.assert_no_ack_file(test_cases[0])
    '''

    def test_lambda_handler_extended_attributes_invalid_key(self):
        """
        Tests that for an extended attributes file (prefix starts with 'Vaccination_Extended_Attributes'):
        Where the filename is otherwise invalid:
        * The file is added to the audit table with a status of 'Failed'
        * The queue_name stored is 'unknown'
        * The file is moved to the archive/ folder in the source bucket
        * No SQS message is sent
        * No ack file is created
        """

        # Build an extended attributes file.
        # FileDetails supports this when vaccine_type starts with 'Vaccination_Extended_Attributes'.
        test_cases = [MockFileDetails.extended_attributes_file]
        invalid_file_key = "Vaccination_Extended_Attributes_invalid_20000101T00000001.csv"
        # Put file in source bucket
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=invalid_file_key,
            Body=MOCK_EXTENDED_ATTRIBUTES_FILE_CONTENT,
        )

        # TODO: rewrite the bucket patches to use moto

        # Patch uuid4 (message id), and don't move the file
        with (
            patch("file_name_processor.uuid4", return_value=test_cases[0].message_id),
            patch(
                "file_name_processor.copy_file_to_external_bucket",
                side_effect=lambda src_bucket, key, dst_bucket, dst_key, exp_owner, exp_src_owner: (
                    # effectively do nothing
                    None,
                ),
            ),
        ):
            lambda_handler(self.make_event([self.make_record(invalid_file_key)]), None)

        # Assert audit table entry captured with Failed and queue_name set to the identifier.
        # Assert that the ClientError message is an InvalidFileKeyError.
        table_items = self.get_audit_table_items()
        self.assertEqual(len(table_items), 1)
        item = table_items[0]
        self.assertEqual(item[AuditTableKeys.MESSAGE_ID]["S"], test_cases[0].message_id)
        self.assertEqual(item[AuditTableKeys.FILENAME]["S"], invalid_file_key)
        self.assertEqual(item[AuditTableKeys.QUEUE_NAME]["S"], "unknown")
        self.assertEqual(item[AuditTableKeys.TIMESTAMP]["S"], test_cases[0].created_at_formatted_string)
        self.assertEqual(item[AuditTableKeys.STATUS]["S"], "Failed")
        self.assertEqual(
            item[AuditTableKeys.ERROR_DETAILS]["S"],
            "Initial file validation failed: invalid extended attributes file key format",
        )
        self.assertEqual(item[AuditTableKeys.EXPIRES_AT]["N"], str(test_cases[0].expires_at))
        # File should be moved to source under archive/
        dest_key = f"archive/{invalid_file_key}"
        print(f" destination file is at {s3_client.list_objects(Bucket=BucketNames.SOURCE)}")
        retrieved = s3_client.get_object(Bucket=BucketNames.SOURCE, Key=dest_key)
        self.assertIsNotNone(retrieved)

        # No SQS and no ack file
        self.assert_no_sqs_message()
        self.assert_no_ack_file(test_cases[0])

    @patch("elasticache.get_redis_client")
    def test_lambda_invalid_file_key_no_other_files_in_queue(self, mock_get_redis_client):
        """
        Tests that when the file_key is invalid:
        * The file is added to the audit table with a status of 'Not processed - Invalid filename'
        * The message is not sent to SQS
        * The failure inf_ack file is created
        """
        mock_redis = fakeredis.FakeStrictRedis()
        mock_redis.hget = Mock(side_effect=self.mock_hget)
        mock_redis.hkeys = Mock(return_value=all_vaccine_types_in_this_test_file)
        mock_get_redis_client.return_value = mock_redis

        invalid_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=invalid_file_key,
            Body=MOCK_BATCH_FILE_CONTENT,
        )
        file_details = deepcopy(MockFileDetails.ravs_rsv_1)
        file_details.file_key = invalid_file_key
        file_details.ack_file_key = self.get_ack_file_key(invalid_file_key)
        file_details.sqs_message_body["filename"] = invalid_file_key

        with (  # noqa: E999
            patch(  # noqa: E999
                "file_name_processor.validate_vaccine_type_permissions"  # noqa: E999
            ) as mock_validate_vaccine_type_permissions,  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
        ):  # noqa: E999
            lambda_handler(self.make_event([self.make_record(file_details.file_key)]), None)

        expected_table_items = [
            {
                "message_id": {"S": file_details.message_id},
                "filename": {"S": file_details.file_key},
                "queue_name": {"S": "unknown_unknown"},
                "status": {"S": "Failed"},
                "error_details": {"S": "Initial file validation failed: invalid file key"},
                "timestamp": {"S": file_details.created_at_formatted_string},
                "expires_at": {"N": str(file_details.expires_at)},
            }
        ]
        self.assertEqual(self.get_audit_table_items(), expected_table_items)
        mock_validate_vaccine_type_permissions.assert_not_called()
        self.assert_ack_file_contents(file_details)
        self.assert_no_sqs_message()

    @patch("elasticache.get_redis_client")
    def test_lambda_invalid_permissions(self, mock_get_redis_client):
        """
        Tests that when the file permissions are invalid:
        * The file is added to the audit table with a status of 'Not processed - Unauthorised'
        * The message is not sent to SQS
        * The failure inf_ack file is created
        """
        mock_redis = fakeredis.FakeStrictRedis()
        # Mock the supplier permissions with a value which doesn't include the requested Flu permissions
        mock_hget = create_mock_hget({"X8E5B": "RAVS"}, {})
        mock_redis.hget = Mock(side_effect=mock_hget)
        mock_redis.hkeys = Mock(return_value=all_vaccine_types_in_this_test_file)
        mock_get_redis_client.return_value = mock_redis

        file_details = deepcopy(MockFileDetails.ravs_rsv_1)
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=file_details.file_key,
            Body=MOCK_BATCH_FILE_CONTENT,
        )

        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=file_details.message_id),  # noqa: E999
        ):  # noqa: E999
            lambda_handler(self.make_event([self.make_record(file_details.file_key)]), None)

        expected_table_items = [
            {
                "message_id": {"S": file_details.message_id},
                "filename": {"S": file_details.file_key},
                "queue_name": {"S": "RAVS_RSV"},
                "status": {"S": "Not processed - Unauthorised"},
                "error_details": {"S": "Initial file validation failed: RAVS does not have permissions for RSV"},
                "timestamp": {"S": file_details.created_at_formatted_string},
                "expires_at": {"N": str(file_details.expires_at)},
            }
        ]
        self.assertEqual(self.get_audit_table_items(), expected_table_items)
        self.assert_no_sqs_message()
        self.assert_ack_file_contents(file_details)

    @patch("elasticache.get_redis_client")
    def test_lambda_adds_event_to_audit_table_as_failed_when_unexpected_exception_is_caught(self, mock_get_redis_client):
        """
        Tests that when an unexpected error occurs e.g. an unexpected exception when validating permissions:
        * The file is added to the audit table with a status of 'Failed' and the reason
        * The message is not sent to SQS
        * The failure inf_ack file is created
        """
        mock_redis = fakeredis.FakeStrictRedis()
        mock_redis.hget = Mock(side_effect=self.mock_hget)
        mock_redis.hkeys = Mock(return_value=all_vaccine_types_in_this_test_file)
        mock_get_redis_client.return_value = mock_redis

        test_file_details = MockFileDetails.emis_flu
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=test_file_details.file_key,
            Body=MOCK_BATCH_FILE_CONTENT,
        )

        with (  # noqa: E999
            patch("file_name_processor.uuid4", return_value=test_file_details.message_id),  # noqa: E999
            patch(
                "file_name_processor.validate_vaccine_type_permissions",
                side_effect=Exception("Some unexpected exception"),
            ),
        ):  # noqa: E999
            lambda_handler(self.make_event([self.make_record(test_file_details.file_key)]), None)

        expected_table_items = [
            {
                "message_id": {"S": test_file_details.message_id},
                "filename": {"S": test_file_details.file_key},
                "queue_name": {"S": "EMIS_FLU"},
                "status": {"S": "Failed"},
                "error_details": {"S": "Some unexpected exception"},
                "timestamp": {"S": test_file_details.created_at_formatted_string},
                "expires_at": {"N": str(test_file_details.expires_at)},
            }
        ]
        self.assertEqual(self.get_audit_table_items(), expected_table_items)
        self.assert_ack_file_contents(test_file_details)
        self.assert_no_sqs_message()


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_dynamodb
@mock_sqs
@mock_firehose
class TestUnexpectedBucket(TestCase):
    """Tests for lambda_handler when an unexpected bucket name is used"""

    def setUp(self):
        GenericSetUp(s3_client, firehose_client, sqs_client, dynamodb_client)

    def tearDown(self):
        GenericTearDown(s3_client, firehose_client, sqs_client, dynamodb_client)

    @patch("elasticache.get_redis_client")
    def test_unexpected_bucket_name(self, mock_get_redis_client):
        """Tests if unknown bucket name is handled in lambda_handler"""
        mock_redis = Mock()
        mock_redis.hget.side_effect = create_mock_hget({"X8E5B": "RAVS"}, {})
        mock_redis.hkeys.return_value = all_vaccine_types_in_this_test_file
        mock_get_redis_client.return_value = mock_redis

        ravs_record = MockFileDetails.ravs_rsv_1
        record = {
            "s3": {
                "bucket": {"name": "unknown-bucket"},
                "object": {"key": ravs_record.file_key},
            }
        }

        with patch("file_name_processor.logger") as mock_logger:
            result = handle_record(record)

            self.assertEqual(result["statusCode"], 500)
            self.assertIn("unexpected bucket name", result["message"])
            self.assertEqual(result["file_key"], ravs_record.file_key)
            self.assertEqual(result["vaccine_type"], ravs_record.vaccine_type)
            self.assertEqual(result["supplier"], ravs_record.supplier)

            mock_logger.error.assert_called_once()
            args = mock_logger.error.call_args[0]
            self.assertIn("Unable to process file", args[0])
            self.assertIn(ravs_record.file_key, args)
            self.assertIn("unknown-bucket", args)

    def test_unexpected_bucket_name_with_extended_attributes_file(self):
        """Tests if extended attributes file is handled when bucket name is incorrect"""
        valid_file_key = "Vaccination_Extended_Attributes_V1_5_X8E5B_20000101T00000001.csv"
        record = {
            "s3": {
                "bucket": {"name": "unknown-bucket"},
                "object": {"key": valid_file_key},
            }
        }

        with patch("file_name_processor.logger") as mock_logger:
            result = handle_record(record)

            self.assertEqual(result["statusCode"], 500)
            self.assertIn("unexpected bucket name", result["message"])
            self.assertEqual(result["file_key"], valid_file_key)
            self.assertEqual(result["vaccine_supplier_info"], f"X8E5B_{EXTENDED_ATTRIBUTES_VACC_TYPE}")

            mock_logger.error.assert_called_once()
            args = mock_logger.error.call_args[0]
            self.assertIn("Unable to process file", args[0])
            self.assertIn(valid_file_key, args)
            self.assertIn("unknown-bucket", args)

    def test_unexpected_bucket_name_and_filename_validation_fails(self):
        """Tests if filename validation error is handled when bucket name is incorrect"""
        invalid_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        record = {
            "s3": {
                "bucket": {"name": "unknown-bucket"},
                "object": {"key": invalid_file_key},
            }
        }

        with patch("file_name_processor.logger") as mock_logger:
            result = handle_record(record)

            self.assertEqual(result["statusCode"], 500)
            self.assertEqual(
                f"Failed to process file due to unexpected bucket name unknown-bucket and file key {invalid_file_key}",
                result["message"],
            )
            self.assertEqual(result["file_key"], invalid_file_key)
            self.assertEqual(result["vaccine_type"], "unknown")
            self.assertEqual(result["supplier"], "unknown")

            mock_logger.error.assert_called_once()
            args = mock_logger.error.call_args[0]
            self.assertIn("Unable to process file", args[0])
            self.assertIn(invalid_file_key, args)
            self.assertIn("unknown-bucket", args)


class TestMainEntryPoint(TestCase):
    def test_run_local_constructs_event_and_calls_lambda_handler(self):
        test_args = [
            "file_name_processor.py",
            "--bucket",
            "test-bucket",
            "--key",
            "some/path/file.csv",
        ]

        expected_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "some/path/file.csv"},
                    }
                }
            ]
        }

        with (
            patch.object(sys, "argv", test_args),
            patch("file_name_processor.lambda_handler") as mock_lambda_handler,
            patch("file_name_processor.print") as mock_print,
        ):
            import file_name_processor

            file_name_processor.run_local()

            mock_lambda_handler.assert_called_once_with(event=expected_event, context={})
            mock_print.assert_called()
