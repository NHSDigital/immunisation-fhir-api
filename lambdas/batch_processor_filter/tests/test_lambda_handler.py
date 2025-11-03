import copy
import json
from json import JSONDecodeError
from unittest import TestCase
from unittest.mock import ANY, Mock, call, patch

import boto3
import botocore
from moto import mock_aws

from batch_file_created_event import BatchFileCreatedEvent
from exceptions import (
    EventAlreadyProcessingForSupplierAndVaccTypeError,
    InvalidBatchSizeError,
)
from testing_utils import (
    MOCK_ENVIRONMENT_DICT,
    add_entry_to_mock_table,
    get_audit_entry_status_by_id,
    make_sqs_record,
)

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from common.clients import REGION_NAME
    from constants import (
        AUDIT_TABLE_FILENAME_GSI,
        AUDIT_TABLE_NAME,
        AUDIT_TABLE_QUEUE_NAME_GSI,
        SPLUNK_FIREHOSE_STREAM_NAME,
        AuditTableKeys,
        FileStatus,
    )
    from lambda_handler import lambda_handler

sqs_client = boto3.client("sqs", region_name=REGION_NAME)
dynamodb_client = boto3.client("dynamodb", region_name=REGION_NAME)
s3_client = boto3.client("s3", region_name=REGION_NAME)


@mock_aws
class TestLambdaHandler(TestCase):
    default_batch_file_event: BatchFileCreatedEvent = BatchFileCreatedEvent(
        message_id="df0b745c-b8cb-492c-ba84-8ea28d9f51d5",
        vaccine_type="MENACWY",
        supplier="TESTSUPPLIER",
        permission=["some-permissions"],
        filename="Menacwy_Vaccinations_v5_TEST_20250820T10210000.csv",
        created_at_formatted_string="20250826T14372600",
    )
    mock_queue_url = MOCK_ENVIRONMENT_DICT.get("QUEUE_URL")
    mock_source_bucket = MOCK_ENVIRONMENT_DICT.get("SOURCE_BUCKET_NAME")
    mock_ack_bucket = MOCK_ENVIRONMENT_DICT.get("ACK_BUCKET_NAME")

    def setUp(self):
        dynamodb_client.create_table(
            TableName=AUDIT_TABLE_NAME,
            KeySchema=[{"AttributeName": AuditTableKeys.MESSAGE_ID, "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": AuditTableKeys.MESSAGE_ID, "AttributeType": "S"},
                {"AttributeName": AuditTableKeys.FILENAME, "AttributeType": "S"},
                {"AttributeName": AuditTableKeys.QUEUE_NAME, "AttributeType": "S"},
                {"AttributeName": AuditTableKeys.STATUS, "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            GlobalSecondaryIndexes=[
                {
                    "IndexName": AUDIT_TABLE_FILENAME_GSI,
                    "KeySchema": [{"AttributeName": AuditTableKeys.FILENAME, "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                },
                {
                    "IndexName": AUDIT_TABLE_QUEUE_NAME_GSI,
                    "KeySchema": [
                        {"AttributeName": AuditTableKeys.QUEUE_NAME, "KeyType": "HASH"},
                        {"AttributeName": AuditTableKeys.STATUS, "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                },
            ],
        )
        sqs_client.create_queue(
            QueueName="imms-batch-metadata-queue.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )

        for bucket_name in [self.mock_source_bucket, self.mock_ack_bucket]:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": REGION_NAME},
            )

        self.logger_patcher = patch("batch_processor_filter_service.logger")
        self.mock_logger = self.logger_patcher.start()
        self.exception_decorator_logger_patcher = patch("exception_decorator.logger")
        self.mock_exception_decorator_logger = self.exception_decorator_logger_patcher.start()
        self.firehose_log_patcher = patch("batch_processor_filter_service.send_log_to_firehose")
        self.mock_firehose_send_log = self.firehose_log_patcher.start()

    def tearDown(self):
        dynamodb_client.delete_table(TableName=AUDIT_TABLE_NAME)
        sqs_client.delete_queue(QueueUrl=self.mock_queue_url)

        for bucket_name in [self.mock_source_bucket, self.mock_ack_bucket]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                # Must delete objects before bucket can be deleted
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

        patch.stopall()

    def _assert_source_file_moved(self, filename: str):
        """Check used in the duplicate scenario to validate that the original uploaded file is moved"""
        with self.assertRaises(botocore.exceptions.ClientError) as exc:
            s3_client.get_object(Bucket=self.mock_source_bucket, Key=filename)

        self.assertEqual(
            str(exc.exception),
            "An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist.",
        )
        archived_object = s3_client.get_object(Bucket=self.mock_source_bucket, Key=f"archive/{filename}")
        self.assertIsNotNone(archived_object)

    def _assert_ack_file_created(self, ack_file_key: str):
        """Check used in duplicate scenario to validate that the failure ack was created"""
        ack_file = s3_client.get_object(Bucket=self.mock_ack_bucket, Key=f"ack/{ack_file_key}")
        self.assertIsNotNone(ack_file)

    def test_lambda_handler_raises_error_when_empty_batch_received(self):
        with self.assertRaises(InvalidBatchSizeError) as exc:
            lambda_handler({"Records": []}, Mock())

        self.assertEqual(str(exc.exception), "Received 0 records, expected 1")

    def test_lambda_handler_raises_error_when_more_than_one_record_in_batch(self):
        with self.assertRaises(InvalidBatchSizeError) as exc:
            lambda_handler(
                {
                    "Records": [
                        make_sqs_record(self.default_batch_file_event),
                        make_sqs_record(self.default_batch_file_event),
                    ]
                },
                Mock(),
            )

        self.assertEqual(str(exc.exception), "Received 2 records, expected 1")

    def test_lambda_handler_decorator_logs_unhandled_exceptions(self):
        """The exception decorator should log the error when an unhandled exception occurs"""
        with self.assertRaises(JSONDecodeError):
            lambda_handler({"Records": [{"body": "{'malformed}"}]}, Mock())

        self.mock_exception_decorator_logger.error.assert_called_once_with(
            "An unhandled exception occurred in the batch processor filter Lambda",
            exc_info=ANY,
        )

    def test_lambda_handler_handles_duplicate_file_scenario(self):
        """Should update the audit table status to duplicate for the incoming record"""
        # Add the duplicate entry that has already been processed
        add_entry_to_mock_table(
            dynamodb_client,
            AUDIT_TABLE_NAME,
            self.default_batch_file_event,
            FileStatus.PROCESSED,
        )
        duplicate_file_event = copy.deepcopy(self.default_batch_file_event)
        duplicate_file_event["message_id"] = "fc9008b7-3865-4dcf-88b8-fc4abafff5f8"
        test_file_name = duplicate_file_event["filename"]

        # Add the audit record for the incoming event
        add_entry_to_mock_table(dynamodb_client, AUDIT_TABLE_NAME, duplicate_file_event, FileStatus.QUEUED)

        # Create the source file in S3
        s3_client.put_object(Bucket=self.mock_source_bucket, Key=test_file_name)

        lambda_handler({"Records": [make_sqs_record(duplicate_file_event)]}, Mock())

        status = get_audit_entry_status_by_id(dynamodb_client, AUDIT_TABLE_NAME, duplicate_file_event["message_id"])
        self.assertEqual(status, "Not processed - Duplicate")

        sqs_messages = sqs_client.receive_message(QueueUrl=self.mock_queue_url)
        self.assertEqual(sqs_messages.get("Messages", []), [])
        self._assert_source_file_moved(test_file_name)
        self._assert_ack_file_created("Menacwy_Vaccinations_v5_TEST_20250820T10210000_InfAck_20250826T14372600.csv")

        self.mock_logger.error.assert_called_once_with(
            "A duplicate file has already been processed. Filename: %s", test_file_name
        )

    def test_lambda_handler_raises_error_when_event_already_processing_for_supplier_and_vacc_type(
        self,
    ):
        """Should raise exception so that the event is returned to the originating queue to be retried later"""
        test_cases = {
            (
                "Event is already being processed for supplier + vacc type queue",
                FileStatus.PROCESSING,
            ),
            (
                "There is a failed event to be checked in supplier + vacc type queue",
                FileStatus.FAILED,
            ),
        }

        for msg, file_status in test_cases:
            self.mock_logger.reset_mock()
            with self.subTest(msg=msg):
                # Add an audit entry for a batch event that is already processing or failed
                add_entry_to_mock_table(
                    dynamodb_client,
                    AUDIT_TABLE_NAME,
                    self.default_batch_file_event,
                    file_status,
                )

                test_event: BatchFileCreatedEvent = BatchFileCreatedEvent(
                    message_id="3b60c4f7-ef67-43c7-8f0d-4faee04d7d0e",
                    vaccine_type="MENACWY",  # Same vacc type
                    supplier="TESTSUPPLIER",  # Same supplier
                    permission=["some-permissions"],
                    filename="Menacwy_Vaccinations_v5_TEST_20250826T15003000.csv",  # Different timestamp
                    created_at_formatted_string="20250826T15003000",
                )
                # Add the audit record for the incoming event
                add_entry_to_mock_table(dynamodb_client, AUDIT_TABLE_NAME, test_event, FileStatus.QUEUED)

                with self.assertRaises(EventAlreadyProcessingForSupplierAndVaccTypeError) as exc:
                    lambda_handler({"Records": [make_sqs_record(test_event)]}, Mock())

                self.assertEqual(
                    str(exc.exception),
                    "Batch event already processing for supplier: TESTSUPPLIER and vacc type: MENACWY",
                )

                status = get_audit_entry_status_by_id(dynamodb_client, AUDIT_TABLE_NAME, test_event["message_id"])
                self.assertEqual(status, "Queued")

                sqs_messages = sqs_client.receive_message(QueueUrl=self.mock_queue_url)
                self.assertEqual(sqs_messages.get("Messages", []), [])

                self.mock_logger.info.assert_has_calls(
                    [
                        call(
                            "Received batch file event for filename: %s with message id: %s",
                            "Menacwy_Vaccinations_v5_TEST_20250826T15003000.csv",
                            "3b60c4f7-ef67-43c7-8f0d-4faee04d7d0e",
                        ),
                        call(
                            "Batch event already processing for supplier and vacc type. Filename: %s",
                            "Menacwy_Vaccinations_v5_TEST_20250826T15003000.csv",
                        ),
                    ]
                )

    def test_lambda_handler_processes_event_successfully(self):
        """Should update the audit entry status to Processing and forward to SQS"""
        add_entry_to_mock_table(
            dynamodb_client,
            AUDIT_TABLE_NAME,
            self.default_batch_file_event,
            FileStatus.QUEUED,
        )

        lambda_handler({"Records": [make_sqs_record(self.default_batch_file_event)]}, Mock())

        status = get_audit_entry_status_by_id(
            dynamodb_client,
            AUDIT_TABLE_NAME,
            self.default_batch_file_event["message_id"],
        )
        self.assertEqual(status, "Processing")

        sqs_messages = sqs_client.receive_message(QueueUrl=self.mock_queue_url)
        self.assertEqual(len(sqs_messages.get("Messages", [])), 1)
        self.assertDictEqual(
            json.loads(sqs_messages["Messages"][0]["Body"]),
            dict(self.default_batch_file_event),
        )

        expected_success_log_message = (
            f"File forwarded for processing by ECS. Filename: {self.default_batch_file_event['filename']}"
        )
        self.mock_logger.info.assert_has_calls(
            [
                call(
                    "Received batch file event for filename: %s with message id: %s",
                    "Menacwy_Vaccinations_v5_TEST_20250820T10210000.csv",
                    "df0b745c-b8cb-492c-ba84-8ea28d9f51d5",
                ),
                call(expected_success_log_message),
            ]
        )
        self.mock_firehose_send_log.assert_called_once_with(
            stream_name=SPLUNK_FIREHOSE_STREAM_NAME,
            log_data={**self.default_batch_file_event, "message": expected_success_log_message},
        )

    def test_lambda_handler_processes_event_successfully_when_event_for_same_supplier_and_vacc_already_processed(
        self,
    ):
        """Should update the audit entry status to Processing and forward to SQS when there is already a file for
        the same supplier and vaccine type in the audit table but it is no longer in Processing state
        """
        add_entry_to_mock_table(
            dynamodb_client,
            AUDIT_TABLE_NAME,
            self.default_batch_file_event,
            FileStatus.PROCESSED,
        )

        test_event: BatchFileCreatedEvent = BatchFileCreatedEvent(
            message_id="3b60c4f7-ef67-43c7-8f0d-4faee04d7d0e",
            vaccine_type="MENACWY",  # Same vacc type
            supplier="TESTSUPPLIER",  # Same supplier
            permission=["some-permissions"],
            filename="Menacwy_Vaccinations_v5_TEST_20250826T15003000.csv",  # Different timestamp
            created_at_formatted_string="20250826T15003000",
        )
        add_entry_to_mock_table(dynamodb_client, AUDIT_TABLE_NAME, test_event, FileStatus.QUEUED)

        lambda_handler({"Records": [make_sqs_record(test_event)]}, Mock())

        status = get_audit_entry_status_by_id(dynamodb_client, AUDIT_TABLE_NAME, test_event["message_id"])
        self.assertEqual(status, "Processing")

        sqs_messages = sqs_client.receive_message(QueueUrl=self.mock_queue_url)
        self.assertEqual(len(sqs_messages.get("Messages", [])), 1)
        self.assertDictEqual(json.loads(sqs_messages["Messages"][0]["Body"]), dict(test_event))

        expected_success_log_message = f"File forwarded for processing by ECS. Filename: {test_event['filename']}"
        self.mock_logger.info.assert_has_calls(
            [
                call(
                    "Received batch file event for filename: %s with message id: %s",
                    "Menacwy_Vaccinations_v5_TEST_20250826T15003000.csv",
                    "3b60c4f7-ef67-43c7-8f0d-4faee04d7d0e",
                ),
                call(expected_success_log_message),
            ]
        )
        self.mock_firehose_send_log.assert_called_once_with(
            stream_name=SPLUNK_FIREHOSE_STREAM_NAME, log_data={**test_event, "message": expected_success_log_message}
        )
