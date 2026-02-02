"""Tests for the functions in the update_ack_file module."""

import copy
import json
import os
import unittest
from io import StringIO
from unittest.mock import patch

from boto3 import client as boto3_client
from moto import mock_aws

from utils.generic_setup_and_teardown_for_ack_backend import (
    GenericSetUp,
    GenericTearDown,
)
from utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    REGION_NAME,
    BucketNames,
)
from utils.utils_for_ack_backend_tests import (
    MOCK_MESSAGE_DETAILS,
    generate_expected_ack_content,
    generate_expected_ack_file_row,
    generate_expected_json_ack_content,
    generate_expected_json_ack_file_element,
    generate_sample_existing_ack_content,
    generate_sample_existing_json_ack_content,
    obtain_current_ack_file_content,
    obtain_current_json_ack_file_content,
    setup_existing_ack_file,
)
from utils.values_for_ack_backend_tests import DefaultValues, ValidValues

with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from update_ack_file import (
        complete_batch_file_process,
        create_ack_data,
        obtain_current_ack_content,
        obtain_current_json_ack_content,
        update_ack_file,
        update_json_ack_file,
    )

firehose_client = boto3_client("firehose", region_name=REGION_NAME)


@patch.dict(os.environ, MOCK_ENVIRONMENT_DICT)
@mock_aws
class TestUpdateAckFile(unittest.TestCase):
    """Tests for the functions in the update_ack_file module."""

    def setUp(self) -> None:
        self.s3_client = boto3_client("s3", region_name=REGION_NAME)
        GenericSetUp(s3_client=self.s3_client)

        # MOCK SOURCE FILE WITH 100 ROWS TO SIMULATE THE SCENARIO WHERE THE ACK FILE IS NOT FULL.
        # TODO: Test all other scenarios.
        mock_source_file_with_100_rows = StringIO("\n".join(f"Row {i}" for i in range(1, 101)))
        self.s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{MOCK_MESSAGE_DETAILS.file_key}",
            Body=mock_source_file_with_100_rows.getvalue(),
        )
        self.logger_patcher = patch("update_ack_file.logger")
        self.mock_logger = self.logger_patcher.start()

        self.ack_bucket_patcher = patch("update_ack_file.ACK_BUCKET_NAME", BucketNames.DESTINATION)
        self.ack_bucket_patcher.start()
        self.source_bucket_patcher = patch("update_ack_file.SOURCE_BUCKET_NAME", BucketNames.SOURCE)
        self.source_bucket_patcher.start()

        self.get_ingestion_start_time_by_message_id_patcher = patch(
            "update_ack_file.get_ingestion_start_time_by_message_id"
        )
        self.mock_get_ingestion_start_time_by_message_id = self.get_ingestion_start_time_by_message_id_patcher.start()
        self.mock_get_ingestion_start_time_by_message_id.return_value = 3456

        self.get_record_and_failure_count_patcher = patch("update_ack_file.get_record_count_and_failures_by_message_id")
        self.mock_get_record_and_failure_count = self.get_record_and_failure_count_patcher.start()

        self.update_audit_table_item_patcher = patch("update_ack_file.update_audit_table_item")
        self.mock_update_audit_table_item = self.update_audit_table_item_patcher.start()

        self.datetime_patcher = patch("update_ack_file.time")
        self.mock_datetime = self.datetime_patcher.start()
        self.mock_datetime.strftime.return_value = "7890"

        self.generate_send_patcher = patch("update_ack_file.generate_and_send_logs")
        self.mock_generate_send = self.generate_send_patcher.start()

    def tearDown(self) -> None:
        GenericTearDown(s3_client=self.s3_client)

    def validate_ack_file_content(
        self,
        incoming_messages: list[dict],
        existing_file_content: str = ValidValues.ack_headers,
    ) -> None:
        """
        Obtains the ack file content and ensures that it matches the expected content (expected content is based
        on the incoming messages).
        """
        actual_ack_file_content = obtain_current_ack_file_content(self.s3_client)
        expected_ack_file_content = generate_expected_ack_content(incoming_messages, existing_file_content)
        self.assertEqual(expected_ack_file_content, actual_ack_file_content)

    def validate_json_ack_file_content(
        self,
        incoming_messages: list[dict],
        existing_file_content: str = ValidValues.json_ack_initial_content,
    ) -> None:
        """
        Obtains the json ack file content and ensures that it matches the expected content (expected content is based
        on the incoming messages).
        """
        actual_ack_file_content = obtain_current_json_ack_file_content(
            self.s3_client, MOCK_MESSAGE_DETAILS.temp_json_ack_file_key
        )
        expected_ack_file_content = generate_expected_json_ack_content(incoming_messages, existing_file_content)
        self.assertEqual(expected_ack_file_content, actual_ack_file_content)

    def test_update_ack_file(self):
        """Test that update_ack_file correctly creates the ack file when there was no existing ack file"""

        test_cases = [
            {
                "description": "Single successful row",
                "input_rows": [ValidValues.ack_data_success_dict],
                "expected_rows": [generate_expected_ack_file_row(success=True, imms_id=DefaultValues.imms_id)],
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
                    generate_expected_ack_file_row(success=True, imms_id=DefaultValues.imms_id),
                    generate_expected_ack_file_row(
                        success=False,
                        imms_id="TEST_IMMS_ID_1",
                        diagnostics="DIAGNOSTICS",
                    ),
                    generate_expected_ack_file_row(success=False, imms_id="", diagnostics="DIAGNOSTICS"),
                    generate_expected_ack_file_row(success=False, imms_id="", diagnostics="DIAGNOSTICS"),
                    generate_expected_ack_file_row(success=True, imms_id="TEST_IMMS_ID_2"),
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
                    generate_expected_ack_file_row(success=False, imms_id="", diagnostics="Error 1"),
                    generate_expected_ack_file_row(success=False, imms_id="", diagnostics="Error 2"),
                    generate_expected_ack_file_row(success=False, imms_id="", diagnostics="Error 3"),
                ],
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case["description"]):
                update_ack_file(
                    file_key=MOCK_MESSAGE_DETAILS.file_key,
                    created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
                    ack_data_rows=test_case["input_rows"],
                )

                actual_ack_file_content = obtain_current_ack_file_content(self.s3_client)
                expected_ack_file_content = ValidValues.ack_headers + "\n".join(test_case["expected_rows"]) + "\n"
                self.assertEqual(expected_ack_file_content, actual_ack_file_content)

                self.s3_client.delete_object(
                    Bucket=BucketNames.DESTINATION,
                    Key=MOCK_MESSAGE_DETAILS.temp_ack_file_key,
                )

    def test_update_json_ack_file(self):
        """Test that update_json_ack_file correctly creates the ack file when there was no existing ack file"""

        test_cases = [
            {
                "description": "Single failure row",
                "input_rows": [ValidValues.ack_data_failure_dict],
                "expected_elements": [
                    generate_expected_json_ack_file_element(
                        success=False, imms_id=DefaultValues.imms_id, diagnostics="DIAGNOSTICS"
                    )
                ],
            },
            {
                "description": "With multiple rows",
                "input_rows": [
                    {**ValidValues.ack_data_failure_dict, "IMMS_ID": "TEST_IMMS_ID_1"},
                    ValidValues.ack_data_failure_dict,
                    ValidValues.ack_data_failure_dict,
                ],
                "expected_elements": [
                    generate_expected_json_ack_file_element(
                        success=False,
                        imms_id="TEST_IMMS_ID_1",
                        diagnostics="DIAGNOSTICS",
                    ),
                    generate_expected_json_ack_file_element(success=False, imms_id="", diagnostics="DIAGNOSTICS"),
                    generate_expected_json_ack_file_element(success=False, imms_id="", diagnostics="DIAGNOSTICS"),
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
                "expected_elements": [
                    generate_expected_json_ack_file_element(success=False, imms_id="", diagnostics="Error 1"),
                    generate_expected_json_ack_file_element(success=False, imms_id="", diagnostics="Error 2"),
                    generate_expected_json_ack_file_element(success=False, imms_id="", diagnostics="Error 3"),
                ],
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case["description"]):
                update_json_ack_file(
                    file_key=MOCK_MESSAGE_DETAILS.file_key,
                    created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
                    ack_data_rows=test_case["input_rows"],
                )

                actual_ack_file_content = obtain_current_json_ack_file_content(
                    self.s3_client, MOCK_MESSAGE_DETAILS.temp_json_ack_file_key
                )
                expected_ack_file_content = copy.deepcopy(ValidValues.json_ack_initial_content)
                for element in test_case["expected_elements"]:
                    expected_ack_file_content["failures"].append(element)
                self.assertEqual(expected_ack_file_content, actual_ack_file_content)
                self.s3_client.delete_object(
                    Bucket=BucketNames.DESTINATION,
                    Key=MOCK_MESSAGE_DETAILS.temp_json_ack_file_key,
                )

    def test_update_ack_file_existing(self):
        """Test that update_ack_file correctly updates the ack file when there was an existing ack file"""
        # Mock existing content in the ack file
        existing_content = generate_sample_existing_ack_content()
        setup_existing_ack_file(MOCK_MESSAGE_DETAILS.temp_ack_file_key, existing_content, self.s3_client)

        ack_data_rows = [
            ValidValues.ack_data_success_dict,
            ValidValues.ack_data_failure_dict,
        ]
        update_ack_file(
            file_key=MOCK_MESSAGE_DETAILS.file_key,
            created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            ack_data_rows=ack_data_rows,
        )

        actual_ack_file_content = obtain_current_ack_file_content(self.s3_client)
        expected_rows = [
            generate_expected_ack_file_row(success=True, imms_id=DefaultValues.imms_id),
            generate_expected_ack_file_row(success=False, imms_id="", diagnostics="DIAGNOSTICS"),
        ]
        expected_ack_file_content = existing_content + "\n".join(expected_rows) + "\n"
        self.assertEqual(expected_ack_file_content, actual_ack_file_content)

    def test_update_json_ack_file_existing(self):
        """Test that update_json_ack_file correctly updates the ack file when there was an existing ack file"""
        # Mock existing content in the ack file
        existing_content = generate_sample_existing_json_ack_content()
        setup_existing_ack_file(
            MOCK_MESSAGE_DETAILS.temp_json_ack_file_key, json.dumps(existing_content), self.s3_client
        )

        ack_data_rows = [
            ValidValues.ack_data_failure_dict,
        ]
        update_json_ack_file(
            file_key=MOCK_MESSAGE_DETAILS.file_key,
            created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            ack_data_rows=ack_data_rows,
        )

        actual_ack_file_content = obtain_current_json_ack_file_content(
            self.s3_client, MOCK_MESSAGE_DETAILS.temp_json_ack_file_key
        )

        expected_rows = [
            generate_expected_json_ack_file_element(success=False, imms_id="", diagnostics="DIAGNOSTICS"),
        ]
        expected_ack_file_content = existing_content
        expected_ack_file_content["failures"].append(expected_rows[0])
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
        setup_existing_ack_file(MOCK_MESSAGE_DETAILS.temp_ack_file_key, existing_content, self.s3_client)
        result = obtain_current_ack_content(MOCK_MESSAGE_DETAILS.temp_ack_file_key)
        self.assertEqual(result.getvalue(), existing_content)

    def test_obtain_current_json_ack_content_file_no_existing(self):
        """Test that when the json ack file does not yet exist, obtain_current_json_ack_content returns the ack headers only."""
        result = obtain_current_json_ack_content(
            MOCK_MESSAGE_DETAILS.message_id, MOCK_MESSAGE_DETAILS.temp_json_ack_file_key
        )
        self.assertEqual(result, ValidValues.json_ack_initial_content)

    def test_obtain_current_json_ack_content_file_exists(self):
        """Test that the existing json ack file content is retrieved and new elements are added."""
        existing_content = generate_sample_existing_json_ack_content()
        setup_existing_ack_file(
            MOCK_MESSAGE_DETAILS.temp_json_ack_file_key, json.dumps(existing_content), self.s3_client
        )
        result = obtain_current_json_ack_content(
            MOCK_MESSAGE_DETAILS.message_id, MOCK_MESSAGE_DETAILS.temp_json_ack_file_key
        )
        self.assertEqual(result, existing_content)

    def test_complete_batch_file_process_json_ack_file(self):
        """Test that complete_batch_file_process completes and moves the JSON ack file."""
        generate_sample_existing_json_ack_content()
        self.s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=f"processing/{MOCK_MESSAGE_DETAILS.file_key}",
            Body="dummy content",
        )
        update_ack_file(
            file_key=MOCK_MESSAGE_DETAILS.file_key,
            created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            ack_data_rows=[ValidValues.ack_data_failure_dict],
        )
        update_json_ack_file(
            file_key=MOCK_MESSAGE_DETAILS.file_key,
            created_at_formatted_string=MOCK_MESSAGE_DETAILS.created_at_formatted_string,
            ack_data_rows=[ValidValues.ack_data_failure_dict],
        )

        self.mock_get_record_and_failure_count.return_value = 10, 1

        complete_batch_file_process(
            message_id=MOCK_MESSAGE_DETAILS.message_id,
            supplier=MOCK_MESSAGE_DETAILS.supplier,
            vaccine_type=MOCK_MESSAGE_DETAILS.vaccine_type,
            created_at_formatted_string="20211120T12000000",
            file_key=MOCK_MESSAGE_DETAILS.file_key,
        )
        result = obtain_current_json_ack_content(
            MOCK_MESSAGE_DETAILS.message_id, MOCK_MESSAGE_DETAILS.archive_json_ack_file_key
        )
        self.assertEqual(result, ValidValues.json_ack_complete_content)


if __name__ == "__main__":
    unittest.main()
