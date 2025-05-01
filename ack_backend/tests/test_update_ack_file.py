"""Tests for the functions in the update_ack_file module."""

import unittest
import os
from unittest.mock import patch
from io import StringIO
from boto3 import client as boto3_client
from moto import mock_s3

from tests.utils_for_ack_backend_tests.values_for_ack_backend_tests import (
    ValidValues,
    DefaultValues,
)
from tests.utils_for_ack_backend_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
    REGION_NAME,
)
from tests.utils_for_ack_backend_tests.generic_setup_and_teardown_for_ack_backend import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_ack_backend_tests.utils_for_ack_backend_tests import (
    setup_existing_ack_file,
    obtain_current_ack_file_content,
    generate_expected_ack_file_row,
    generate_sample_existing_ack_content,
    generate_expected_ack_content,
    MOCK_MESSAGE_DETAILS,
)

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from update_ack_file import (
        obtain_current_ack_content,
        create_ack_data,
        update_ack_file,
    )

s3_client = boto3_client("s3", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)


@patch.dict(os.environ, MOCK_ENVIRONMENT_DICT)
@mock_s3
class TestUpdateAckFile(unittest.TestCase):
    """Tests for the functions in the update_ack_file module."""

    def setUp(self) -> None:
        GenericSetUp(s3_client)

        # MOCK SOURCE FILE WITH 100 ROWS TO SIMULATE THE SCENARIO WHERE THE ACK FILE IS NOT FULL.
        # TODO: Test all other scenarios.
        mock_source_file_with_100_rows = StringIO(
            "\n".join(f"Row {i}" for i in range(1, 101))
        )
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{MOCK_MESSAGE_DETAILS.file_key}",
            Body=mock_source_file_with_100_rows.getvalue(),
        )

    def tearDown(self) -> None:
        GenericTearDown(s3_client)

    def validate_ack_file_content(
        self,
        incoming_messages: list[dict],
        existing_file_content: str = ValidValues.ack_headers,
    ) -> None:
        """
        Obtains the ack file content and ensures that it matches the expected content (expected content is based
        on the incoming messages).
        """
        actual_ack_file_content = obtain_current_ack_file_content()
        expected_ack_file_content = generate_expected_ack_content(
            incoming_messages, existing_file_content
        )
        self.assertEqual(expected_ack_file_content, actual_ack_file_content)

    def test_update_ack_file(self):
        """Test that update_ack_file correctly creates the ack file when there was no existing ack file"""

        test_cases = [
            {
                "description": "Single successful row",
                "input_rows": [ValidValues.ack_data_success_dict],
                "expected_rows": [
                    generate_expected_ack_file_row(
                        success=True, imms_id=DefaultValues.imms_id
                    )
                ],
            },
            {
                "description": "With multiple rows - failure and success rows",
                "input_rows": [
                    ValidValues.ack_data_success_dict,
                    {**ValidValues.ack_data_failure_dict, "IMMS_ID": "TEST_IMMS_ID_1"},
                    ValidValues.ack_data_failure_dict,
                    ValidValues.ack_data_failure_dict,
                    {**ValidValues.ack_data_success_dict, "IMMS_ID": "TEST_IMMS_ID_2"},
                ],
                "expected_rows": [
                    generate_expected_ack_file_row(
                        success=True, imms_id=DefaultValues.imms_id
                    ),
                    generate_expected_ack_file_row(
                        success=False,
                        imms_id="TEST_IMMS_ID_1",
                        diagnostics="DIAGNOSTICS",
                    ),
                    generate_expected_ack_file_row(
                        success=False, imms_id="", diagnostics="DIAGNOSTICS"
                    ),
                    generate_expected_ack_file_row(
                        success=False, imms_id="", diagnostics="DIAGNOSTICS"
                    ),
                    generate_expected_ack_file_row(
                        success=True, imms_id="TEST_IMMS_ID_2"
                    ),
                ],
            },
            {
                "description": "Multiple rows With different diagnostics",
                "input_rows": [
                    {
                        **ValidValues.ack_data_failure_dict,
                        "OPERATION_OUTCOME": "Error 1",
                    },
                    {
                        **ValidValues.ack_data_failure_dict,
                        "OPERATION_OUTCOME": "Error 2",
                    },
                    {
                        **ValidValues.ack_data_failure_dict,
                        "OPERATION_OUTCOME": "Error 3",
                    },
                ],
                "expected_rows": [
                    generate_expected_ack_file_row(
                        success=False, imms_id="", diagnostics="Error 1"
                    ),
                    generate_expected_ack_file_row(
                        success=False, imms_id="", diagnostics="Error 2"
                    ),
                    generate_expected_ack_file_row(
                        success=False, imms_id="", diagnostics="Error 3"
                    ),
                ],
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case["description"]):
                update_ack_file(
                    file_key=MOCK_MESSAGE_DETAILS.file_key,
                    message_id=MOCK_MESSAGE_DETAILS.message_id,
                    supplier_queue=MOCK_MESSAGE_DETAILS.queue_name,
                    created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
                    ack_data_rows=test_case["input_rows"],
                )

                actual_ack_file_content = obtain_current_ack_file_content()
                expected_ack_file_content = (
                    ValidValues.ack_headers
                    + "\n".join(test_case["expected_rows"])
                    + "\n"
                )
                self.assertEqual(expected_ack_file_content, actual_ack_file_content)

                s3_client.delete_object(
                    Bucket=BucketNames.DESTINATION,
                    Key=MOCK_MESSAGE_DETAILS.temp_ack_file_key,
                )

    def test_update_ack_file_existing(self):
        """Test that update_ack_file correctly updates the ack file when there was an existing ack file"""
        # Mock existing content in the ack file
        existing_content = generate_sample_existing_ack_content()
        setup_existing_ack_file(
            MOCK_MESSAGE_DETAILS.temp_ack_file_key, existing_content
        )

        ack_data_rows = [
            ValidValues.ack_data_success_dict,
            ValidValues.ack_data_failure_dict,
        ]
        update_ack_file(
            file_key=MOCK_MESSAGE_DETAILS.file_key,
            message_id=MOCK_MESSAGE_DETAILS.message_id,
            supplier_queue=MOCK_MESSAGE_DETAILS.queue_name,
            created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            ack_data_rows=ack_data_rows,
        )

        actual_ack_file_content = obtain_current_ack_file_content()
        expected_rows = [
            generate_expected_ack_file_row(success=True, imms_id=DefaultValues.imms_id),
            generate_expected_ack_file_row(
                success=False, imms_id="", diagnostics="DIAGNOSTICS"
            ),
        ]
        expected_ack_file_content = existing_content + "\n".join(expected_rows) + "\n"
        self.assertEqual(expected_ack_file_content, actual_ack_file_content)

    def test_create_ack_data(self):
        """Test create_ack_data with success and failure cases."""

        success_expected_result = {
            "MESSAGE_HEADER_ID": MOCK_MESSAGE_DETAILS.row_id,
            "HEADER_RESPONSE_CODE": "OK",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "30001",
            "RESPONSE_TYPE": "Business",
            "RESPONSE_CODE": "30001",
            "RESPONSE_DISPLAY": "Success",
            "RECEIVED_TIME": MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": MOCK_MESSAGE_DETAILS.local_id,
            "IMMS_ID": MOCK_MESSAGE_DETAILS.imms_id,
            "OPERATION_OUTCOME": "",
            "MESSAGE_DELIVERY": True,
        }

        failure_expected_result = {
            "MESSAGE_HEADER_ID": MOCK_MESSAGE_DETAILS.row_id,
            "HEADER_RESPONSE_CODE": "Fatal Error",
            "ISSUE_SEVERITY": "Fatal",
            "ISSUE_CODE": "Fatal Error",
            "ISSUE_DETAILS_CODE": "30002",
            "RESPONSE_TYPE": "Business",
            "RESPONSE_CODE": "30002",
            "RESPONSE_DISPLAY": "Business Level Response Value - Processing Error",
            "RECEIVED_TIME": MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": MOCK_MESSAGE_DETAILS.local_id,
            "IMMS_ID": "",
            "OPERATION_OUTCOME": "test diagnostics message",
            "MESSAGE_DELIVERY": False,
        }

        test_cases = [
            {
                "success": True,
                "imms_id": MOCK_MESSAGE_DETAILS.imms_id,
                "expected_result": success_expected_result,
            },
            {
                "success": False,
                "diagnostics": "test diagnostics message",
                "expected_result": failure_expected_result,
            },
        ]

        for test_case in test_cases:
            with self.subTest(f"success is {test_case['success']}"):
                result = create_ack_data(
                    created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
                    local_id=MOCK_MESSAGE_DETAILS.local_id,
                    row_id=MOCK_MESSAGE_DETAILS.row_id,
                    successful_api_response=test_case["success"],
                    diagnostics=test_case.get("diagnostics"),
                    imms_id=test_case.get("imms_id"),
                )
                self.assertEqual(result, test_case["expected_result"])

    def test_obtain_current_ack_content_file_no_existing(self):
        """Test that when the ack file does not yet exist, obtain_current_ack_content returns the ack headers only."""
        result = obtain_current_ack_content(MOCK_MESSAGE_DETAILS.temp_ack_file_key)
        self.assertEqual(result.getvalue(), ValidValues.ack_headers)

    def test_obtain_current_ack_content_file_exists(self):
        """Test that the existing ack file content is retrieved and new rows are added."""
        existing_content = generate_sample_existing_ack_content()
        setup_existing_ack_file(
            MOCK_MESSAGE_DETAILS.temp_ack_file_key, existing_content
        )
        result = obtain_current_ack_content(MOCK_MESSAGE_DETAILS.temp_ack_file_key)
        self.assertEqual(result.getvalue(), existing_content)


if __name__ == "__main__":
    unittest.main()
