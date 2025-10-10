"""Tests for the ack processor lambda handler."""

import json
import os
import unittest
from io import StringIO
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_firehose, mock_s3

from tests.utils.generic_setup_and_teardown_for_ack_backend import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    REGION_NAME,
    BucketNames,
)
from tests.utils.utils_for_ack_backend_tests import (
    setup_existing_ack_file,
    validate_ack_file_content,
)
from tests.utils.values_for_ack_backend_tests import (
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
@mock_s3
@mock_firehose
class TestAckProcessor(unittest.TestCase):
    """Tests for the ack processor lambda handler."""

    def setUp(self) -> None:
        self.s3_client = boto3_client("s3", region_name=REGION_NAME)
        self.firehose_client = boto3_client("firehose", region_name=REGION_NAME)
        GenericSetUp(self.s3_client, self.firehose_client)

        # MOCK SOURCE FILE WITH 100 ROWS TO SIMULATE THE SCENARIO WHERE THE ACK FILE IS NO FULL.
        # TODO: Test all other scenarios.
        mock_source_file_with_100_rows = StringIO("\n".join(f"Row {i}" for i in range(1, 101)))
        self.s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{MOCK_MESSAGE_DETAILS.file_key}",
            Body=mock_source_file_with_100_rows.getvalue(),
        )
        self.logger_info_patcher = patch("common.log_decorator.logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self) -> None:
        GenericTearDown(self.s3_client, self.firehose_client)
        self.mock_logger_info.stop()

    @staticmethod
    def generate_event(test_messages: list[dict]) -> dict:
        """
        Returns an event where each message in the incoming message body list is based on a standard mock message,
        updated with the details from the corresponsing message in the given test_messages list.
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

    def test_lambda_handler_main_multiple_records(self):
        """Test lambda handler with multiple records."""
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
        test_cases = [
            {
                "description": "Multiple messages: all successful",
                "messages": [{"row_id": f"row_{i + 1}"} for i in range(10)],
            },
            {
                "description": "Multiple messages: all with diagnostics (failure messages)",
                "messages": [
                    {
                        "row_id": "row_1",
                        "diagnostics": DiagnosticsDictionaries.UNIQUE_ID_MISSING,
                    },
                    {
                        "row_id": "row_2",
                        "diagnostics": DiagnosticsDictionaries.NO_PERMISSIONS,
                    },
                    {
                        "row_id": "row_3",
                        "diagnostics": DiagnosticsDictionaries.RESOURCE_NOT_FOUND_ERROR,
                    },
                ],
            },
            {
                "description": "Multiple messages: mixture of success and failure messages",
                "messages": [
                    {"row_id": "row_1", "imms_id": "TEST_IMMS_ID"},
                    {
                        "row_id": "row_2",
                        "diagnostics": DiagnosticsDictionaries.UNIQUE_ID_MISSING,
                    },
                    {
                        "row_id": "row_3",
                        "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR,
                    },
                    {"row_id": "row_4"},
                    {
                        "row_id": "row_5",
                        "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR,
                    },
                    {
                        "row_id": "row_6",
                        "diagnostics": DiagnosticsDictionaries.CUSTOM_VALIDATION_ERROR,
                    },
                    {"row_id": "row_7"},
                    {
                        "row_id": "row_8",
                        "diagnostics": DiagnosticsDictionaries.IDENTIFIER_DUPLICATION_ERROR,
                    },
                ],
            },
            {
                "description": "Single row: success",
                "messages": [{"row_id": "row_1"}],
            },
            {
                "description": "Single row: malformed diagnostics info from forwarder",
                "messages": [
                    {
                        "row_id": "row_1",
                        "diagnostics": "SHOULD BE A DICTIONARY, NOT A STRING",
                    }
                ],
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

            # Test scenario where there is an existing ack file
            # TODO: None of the test cases have any existing ack file content?
            with self.subTest(msg=f"Existing ack file: {test_case['description']}"):
                existing_ack_file_content = test_case.get("existing_ack_file_content", "")
                setup_existing_ack_file(
                    MOCK_MESSAGE_DETAILS.temp_ack_file_key,
                    existing_ack_file_content,
                    self.s3_client,
                )
                response = lambda_handler(event=self.generate_event(test_case["messages"]), context={})
                self.assertEqual(response, EXPECTED_ACK_LAMBDA_RESPONSE_FOR_SUCCESS)
                validate_ack_file_content(self.s3_client, test_case["messages"], existing_ack_file_content)

                self.s3_client.delete_object(
                    Bucket=BucketNames.DESTINATION,
                    Key=MOCK_MESSAGE_DETAILS.temp_ack_file_key,
                )

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
