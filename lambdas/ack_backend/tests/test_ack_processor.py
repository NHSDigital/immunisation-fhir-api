"""Tests for the ack processor lambda handler."""

import json
import os
import unittest
from copy import deepcopy
from io import StringIO
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_aws

from utils.generic_setup_and_teardown_for_ack_backend import (
    GenericSetUp,
    GenericTearDown,
)
from utils.mock_environment_variables import (
    AUDIT_TABLE_NAME,
    MOCK_ENVIRONMENT_DICT,
    REGION_NAME,
    BucketNames,
)
from utils.utils_for_ack_backend_tests import (
    add_audit_entry_to_table,
    generate_sample_existing_ack_content,
    validate_ack_file_content,
)
from utils.values_for_ack_backend_tests import (
    EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS,
    MOCK_MESSAGE_DETAILS,
    DiagnosticsDictionaries,
    ValidValues,
)

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from ack_processor import lambda_handler

BASE_SUCCESS_MESSAGE = MOCK_MESSAGE_DETAILS.success_message
BASE_FAILURE_MESSAGE = {
    **{k: v for k, v in BASE_SUCCESS_MESSAGE.items() if k != "imms_id"},
    "diagnostics": DiagnosticsDictionaries.UNIQUE_ID_MISSING,
}


@patch.dict(os.environ, MOCK_ENVIRONMENT_DICT)
@patch("audit_table.AUDIT_TABLE_NAME", AUDIT_TABLE_NAME)
@mock_aws
class TestAckProcessor(unittest.TestCase):
    """Tests for the ack processor lambda handler."""

    def setUp(self) -> None:
        self.s3_client = boto3_client("s3", region_name=REGION_NAME)
        self.firehose_client = boto3_client("firehose", region_name=REGION_NAME)
        self.dynamodb_client = boto3_client("dynamodb", region_name=REGION_NAME)
        GenericSetUp(self.s3_client, self.firehose_client, self.dynamodb_client)

        mock_source_file_with_100_rows = StringIO("\n".join(f"Row {i}" for i in range(1, 101)))
        self.s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{MOCK_MESSAGE_DETAILS.file_key}",
            Body=mock_source_file_with_100_rows.getvalue(),
        )
        self.logger_info_patcher = patch("common.log_decorator.logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self) -> None:
        GenericTearDown(self.s3_client, self.firehose_client, self.dynamodb_client)
        self.mock_logger_info.stop()

    @staticmethod
    def generate_event(test_messages: list[dict]) -> dict:
        """
        Returns an event where each message in the incoming message body list is based on a standard mock message,
        updated with the details from the corresponding message in the given test_messages list.
        """
        incoming_message_body = [
            (
                {**MOCK_MESSAGE_DETAILS.failure_message, **message}
                if message.get("diagnostics")
                else {**MOCK_MESSAGE_DETAILS.success_message, **message}
            )
            for message in test_messages
        ]
        return {"Records": [{"body": json.dumps(incoming_message_body)}]}

    def assert_ack_and_source_file_locations_correct(
        self,
        source_file_key: str,
        tmp_ack_file_key: str,
        complete_ack_file_key: str,
        is_complete: bool,
    ) -> None:
        """Helper function to check the ack and source files have not been moved as the processing is not yet
        complete"""
        if is_complete:
            ack_file = self.s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=complete_ack_file_key)
        else:
            ack_file = self.s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=tmp_ack_file_key)
        self.assertIsNotNone(ack_file["Body"].read())

        full_src_file_key = f"archive/{source_file_key}" if is_complete else f"processing/{source_file_key}"
        src_file = self.s3_client.get_object(Bucket=BucketNames.SOURCE, Key=full_src_file_key)
        self.assertIsNotNone(src_file["Body"].read())

    def assert_audit_entry_status_equals(self, message_id: str, status: str) -> None:
        """Checks the audit entry status is as expected"""
        audit_entry = self.dynamodb_client.get_item(
            TableName=AUDIT_TABLE_NAME, Key={"message_id": {"S": message_id}}
        ).get("Item")

        actual_status = audit_entry.get("status", {}).get("S")
        self.assertEqual(actual_status, status)

    def test_lambda_handler_main_multiple_records(self):
        """Test lambda handler with multiple records."""
        # Set up an audit entry which does not yet have record_count recorded
        add_audit_entry_to_table(self.dynamodb_client, "row")
        # First array of messages: all successful. Rows 1 to 3
        array_of_success_messages = [
            {
                **BASE_SUCCESS_MESSAGE,
                "row_id": f"row^{i}",
                "imms_id": f"imms_{i}",
                "local_id": f"local^{i}",
            }
            for i in range(1, 4)
        ]
        # Second array of messages: all with diagnostics (failure messages). Rows 4 to 7
        array_of_failure_messages = [
            {**BASE_FAILURE_MESSAGE, "row_id": f"row^{i}", "local_id": f"local^{i}"} for i in range(4, 8)
        ]
        # Third array of messages: mixture of success and failure messages. Rows 8 to 11
        array_of_mixed_success_and_failure_messages = [
            {
                **BASE_FAILURE_MESSAGE,
                "row_id": "row^8",
                "local_id": "local^8",
                "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR,
            },
            {
                **BASE_SUCCESS_MESSAGE,
                "row_id": "row^9",
                "imms_id": "imms_9",
                "local_id": "local^9",
            },
            {
                **BASE_SUCCESS_MESSAGE,
                "row_id": "row^10",
                "imms_id": "imms_10",
                "local_id": "local^10",
            },
            {
                **BASE_FAILURE_MESSAGE,
                "row_id": "row^11",
                "local_id": "local^11",
                "diagnostics": DiagnosticsDictionaries.UNHANDLED_ERROR,
            },
        ]

        event = {
            "Records": [
                {"body": json.dumps(array_of_success_messages)},
                {"body": json.dumps(array_of_failure_messages)},
                {"body": json.dumps(array_of_mixed_success_and_failure_messages)},
            ]
        }

        response = lambda_handler(event=event, context={})

        self.assertEqual(response, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)
        validate_ack_file_content(
            self.s3_client,
            [
                *array_of_success_messages,
                *array_of_failure_messages,
                *array_of_mixed_success_and_failure_messages,
            ],
            existing_file_content=ValidValues.ack_headers,
        )

    def test_lambda_handler_main(self):
        """Test lambda handler with consitent ack_file_name and message_template."""
        # Set up an audit entry which does not yet have record_count recorded
        add_audit_entry_to_table(self.dynamodb_client, "row")
        test_cases = [
            {
                "description": "Multiple messages: all successful",
                "messages": [{"row_id": f"row^{i + 1}"} for i in range(10)],
            },
            {
                "description": "Multiple messages: all with diagnostics (failure messages)",
                "messages": [
                    {"row_id": "row^1", "diagnostics": DiagnosticsDictionaries.UNIQUE_ID_MISSING},
                    {"row_id": "row^2", "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS},
                    {"row_id": "row^3", "diagnostics": DiagnosticsDictionaries.RESOURCE_NOT_FOUND_ERROR},
                ],
            },
            {
                "description": "Multiple messages: mixture of success and failure messages",
                "messages": [
                    {"row_id": "row^1", "imms_id": "TEST_IMMS_ID"},
                    {"row_id": "row^2", "diagnostics": DiagnosticsDictionaries.UNIQUE_ID_MISSING},
                    {"row_id": "row^3", "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR},
                    {"row_id": "row^4"},
                    {"row_id": "row^5", "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR},
                    {"row_id": "row^6", "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR},
                    {"row_id": "row^7"},
                    {"row_id": "row^8", "diagnostics": DiagnosticsDictionaries.IDENTIFIER_DUPLICATION_ERROR},
                ],
            },
            {
                "description": "Single row: success",
                "messages": [{"row_id": "row^1"}],
            },
            {
                "description": "Single row: malformed diagnostics info from forwarder",
                "messages": [{"row_id": "row^1", "diagnostics": "SHOULD BE A DICTIONARY, NOT A STRING"}],
            },
        ]

        for test_case in test_cases:
            # Test scenario where there is no existing ack file
            with self.subTest(msg=f"No existing ack file: {test_case['description']}"):
                response = lambda_handler(event=self.generate_event(test_case["messages"]), context={})
                self.assertEqual(response, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)
                validate_ack_file_content(self.s3_client, test_case["messages"])

                self.s3_client.delete_object(
                    Bucket=BucketNames.DESTINATION,
                    Key=MOCK_MESSAGE_DETAILS.temp_ack_file_key,
                )

    def test_lambda_handler_updates_ack_file_but_does_not_mark_complete_when_records_still_remaining(self):
        """
        Test that the batch file process is not marked as complete when not all records have been processed.
        This means:
        - the ack file remains in the TempAck directory
        - the source file remains in the processing directory
        - all ack records in the event are written to the temporary ack
        """
        mock_batch_message_id = "b500efe4-6e75-4768-a38b-6127b3c7b8e0"

        # Original source file had 100 records
        add_audit_entry_to_table(self.dynamodb_client, mock_batch_message_id, record_count=100)
        array_of_success_messages = [
            {
                **BASE_SUCCESS_MESSAGE,
                "row_id": f"{mock_batch_message_id}^{i}",
                "imms_id": f"imms_{i}",
                "local_id": f"local^{i}",
            }
            for i in range(1, 4)
        ]
        test_event = {"Records": [{"body": json.dumps(array_of_success_messages)}]}

        response = lambda_handler(event=test_event, context={})

        self.assertEqual(response, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)
        validate_ack_file_content(
            self.s3_client,
            [*array_of_success_messages],
            existing_file_content=ValidValues.ack_headers,
        )
        self.assert_ack_and_source_file_locations_correct(
            MOCK_MESSAGE_DETAILS.file_key,
            MOCK_MESSAGE_DETAILS.temp_ack_file_key,
            MOCK_MESSAGE_DETAILS.archive_ack_file_key,
            is_complete=False,
        )
        self.assert_audit_entry_status_equals(mock_batch_message_id, "Preprocessed")

    def test_lambda_handler_updates_ack_file_and_marks_complete_when_all_records_processed(self):
        """
        Test that the batch file process is marked as complete when all records have been processed.
        This means:
        - the ack file moves from the TempAck directory to the forwardedFile directory
        - the source file moves from the processing to the archive directory
        - all ack records in the event are appended to the existing temporary ack file
        - the DDB Audit Table status is set as 'Processed'
        """
        mock_batch_message_id = "75db20e6-c0b5-4012-a8bc-f861a1dd4b22"

        # Original source file had 100 records
        add_audit_entry_to_table(self.dynamodb_client, mock_batch_message_id, record_count=100)

        # Previous invocations have already created and added to the temp ack file
        existing_ack_content = generate_sample_existing_ack_content()
        self.s3_client.put_object(
            Bucket=BucketNames.DESTINATION,
            Key=MOCK_MESSAGE_DETAILS.temp_ack_file_key,
            Body=StringIO(existing_ack_content).getvalue(),
        )

        array_of_success_messages = [
            {
                **BASE_SUCCESS_MESSAGE,
                "row_id": f"{mock_batch_message_id}^{i}",
                "imms_id": f"imms_{i}",
                "local_id": f"local^{i}",
            }
            for i in range(50, 101)
        ]

        # Include the EoF message in the event
        all_messages_plus_eof = deepcopy(array_of_success_messages)
        all_messages_plus_eof.append(MOCK_MESSAGE_DETAILS.eof_message)
        test_event = {"Records": [{"body": json.dumps(all_messages_plus_eof)}]}

        response = lambda_handler(event=test_event, context={})

        self.assertEqual(response, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)
        validate_ack_file_content(
            self.s3_client, [*array_of_success_messages], existing_file_content=existing_ack_content, is_complete=True
        )
        self.assert_ack_and_source_file_locations_correct(
            MOCK_MESSAGE_DETAILS.file_key,
            MOCK_MESSAGE_DETAILS.temp_ack_file_key,
            MOCK_MESSAGE_DETAILS.archive_ack_file_key,
            is_complete=True,
        )
        self.assert_audit_entry_status_equals(mock_batch_message_id, "Processed")

    def test_lambda_handler_error_scenarios(self):
        """Test that the lambda handler raises appropriate exceptions for malformed event data."""

        test_cases = [
            {
                "description": "Empty event",
                "event": {},
                "expected_message": "No records found in the event",
            },
            {
                "description": "Malformed JSON in SQS body",
                "event": {"Records": [{""}]},
                "expected_message": "Could not load incoming message body",
            },
        ]

        for test_case in test_cases:
            with self.subTest(msg=test_case["description"]):
                with patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose:
                    with self.assertRaises(ValueError):
                        lambda_handler(event=test_case["event"], context={})
                error_log = mock_send_log_to_firehose.call_args[0][1]
                self.assertIn(test_case["expected_message"], error_log["diagnostics"])


if __name__ == "__main__":
    unittest.main()
