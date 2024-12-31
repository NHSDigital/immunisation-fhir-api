import unittest
from moto import mock_s3, mock_sqs
import os
import json
from boto3 import client as boto3_client
from unittest.mock import patch, MagicMock
from ack_processor import lambda_handler
from update_ack_file import obtain_current_ack_content, create_ack_data, update_ack_file
import boto3
from tests.test_utils_for_ack_backend import (
    DESTINATION_BUCKET_NAME,
    AWS_REGION,
    ValidValues,
    InvalidValues,
    CREATED_AT_FORMATTED_STRING,
)
from constants import Constants
from io import BytesIO, StringIO
from copy import deepcopy
from botocore.exceptions import ClientError
from unittest import TestCase
import uuid


s3_client = boto3_client("s3", region_name=AWS_REGION)
file_name = "COVID19_Vaccinations_v5_YGM41_20240909T13005902.csv"
ack_file_key = "forwardedFile/COVID19_Vaccinations_v5_YGM41_20240909T13005902_BusAck_20241115T13435500.csv"
test_ack_file_key = "forwardedFile/COVID19_Vaccinations_v5_YGM41_20240909T13005902_BusAck_20241115T13455555.csv"
local_id = "111^222"
os.environ["ACK_BUCKET_NAME"] = DESTINATION_BUCKET_NAME
invalid_action_flag_diagnostics = "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"
test_bucket_name = "immunisation-batch-internal-testlambda-data-destinations"


@mock_s3
@mock_sqs
class TestAckProcessor(unittest.TestCase):

    def setup_s3(self):
        """Creates a mock S3 bucket contain a single file different to one created during tests
        to ensure s3 bucket loads correctly."""
        ack_bucket_name = "immunisation-batch-internal-testlambda-data-destinations"
        os.environ["ACK_BUCKET_NAME"] = test_bucket_name
        existing_content = ValidValues.test_ack_header
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )
        s3_client.put_object(Bucket=test_bucket_name, Key="some_other_file", Body=existing_content)

    def setup_existing_ack_file(self, bucket_name, file_key, file_content):
        """Creates a mock S3 bucket and uploads an existing file with the given content."""
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=file_content)

    def create_event(self, test_data):
        """
        Dynamically create the event for tests with multiple records.
        """
        rows = []
        for test_case_row in test_data["rows"]:
            row = self.row_template.copy()
            row.update(test_case_row)
            rows.append(row)
        return {"Records": [{"body": json.dumps(rows)}]}

    row_template = {
        "file_key": file_name,
        "row_id": "123^1",
        "local_id": ValidValues.local_id,
        "action_flag": "create",
        "imms_id": "",
        "created_at_formatted_string": "20241115T13435500",
    }

    def ack_row_order(self, row_input, expected_ack_file_content, actual_ack_file_content):
        """
        Validates that rows in actual_ack_file_content match the full row details in expected_ack_file_content
        and appear in the same order as in row_input.
            expected_ack_file_content (str): Full expected content of the ACK file from test.
            actual_ack_file_content (str): Actual content uploaded to the ACK file.
        """

        for row in row_input:
            row_id = row.get("row_id")
            self.assertIn(f"{row_id}|", actual_ack_file_content)

        # Split expected and uploaded content into lines for line-by-line comparison
        expected_lines = expected_ack_file_content.strip().split("\n")
        uploaded_lines = actual_ack_file_content.strip().split("\n")

        # Check each file content the correct amount of lines
        self.assertEqual(len(expected_lines), len(uploaded_lines))

        # Checks each row in expected and actual ack file outputs has exact match and order
        for i, (expected_line, uploaded_line) in enumerate(zip(expected_lines, uploaded_lines)):
            self.assertEqual(expected_line, uploaded_line)

    def create_expected_ack_content(self, row_input, actual_ack_file_content, expected_ack_file_content):
        """creates test ack rows from using a list containing multiple rows"""
        for i, row in enumerate(row_input):
            diagnostics = row.get("diagnostics", "")
            imms_id = row.get("imms_id", "")
            row_id = row.get("row_id")
            if diagnostics:
                ack_row = (
                    f"{row_id}|Fatal Error|Fatal|Fatal Error|30002|Business|30002|Business Level "
                    f"Response Value - Processing Error|20241115T13435500||111^222|{imms_id}|{diagnostics}|False"
                )
            else:
                ack_row = (
                    f"{row_id}|OK|Information|OK|30001|Business|30001|Success|20241115T13435500|"
                    f"|111^222|{imms_id}||True"
                )

            expected_ack_file_content += ack_row + "\n"

        self.assertEqual(actual_ack_file_content, expected_ack_file_content)
        self.ack_row_order(row_input, expected_ack_file_content, actual_ack_file_content)

    def generate_file_names(self):
        """Generates dynamic file names
        Returns:
            dict: A dictionary containing `file_key_existing`, `ack_file_name`, and `row_template`."""
        file_key_existing = f"COVID19_Vaccinations_v5_DPSREDUCED_{uuid.uuid4().hex}.csv"
        ack_file_name = f"forwardedFile/{file_key_existing.replace('.csv', '_BusAck_20241115T13435500.csv')}"

        row_template = self.row_template.copy()
        row_template.update({"file_key": file_key_existing})

        return {
            "file_key_existing": file_key_existing,
            "ack_file_name": ack_file_name,
            "row_template": row_template,
        }

    def environment_setup(self, ack_file_name, existing_content):
        """
        Generates a file with existing content in the mock s3 bucket and updates row_template.
            test_case_description (str): Description of the test case.
            existing_content (str): The initial content to upload to the file in S3.
        """

        try:
            s3_client.delete_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_name)
        except s3_client.exceptions.NoSuchKey:
            pass

        s3_client.put_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_name, Body=existing_content)

    @patch("log_structure_splunk.firehose_logger")
    def test_lambda_handler_main(self, mock_firehose_logger):
        """Test lambda handler with dynamic ack_file_name and consistent row_template."""
        test_bucket_name = "immunisation-batch-internal-testlambda-data-destinations"
        self.setup_s3()
        existing_content = ValidValues.test_ack_header

        test_cases = [
            {
                "description": "10 success rows (No diagnostics)",
                "rows": [{"row_id": f"row_{i+1}"} for i in range(10)],
            },
            {
                "description": "SQS event with multiple errors",
                "rows": [
                    {"row_id": "row_1", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is NEW"},
                    {"row_id": "row_2", "diagnostics": "unauthorized"},
                    {"row_id": "row_3", "diagnostics": "not found"},
                ],
            },
            {
                "description": "Multiple row processing from SQS event - mixture of success and failure rows",
                "rows": [
                    {"row_id": "row_1", "imms_id": "TEST_IMMS_ID"},
                    {"row_id": "row_2", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is NEW"},
                    {"row_id": "row_3", "diagnostics": "Validation_error"},
                    {"row_id": "row_4"},
                    {"row_id": "row_5", "diagnostics": "Validation_error", "imms_id": "TEST_IMMS_ID"},
                    {"row_id": "row_6", "diagnostics": "Validation_error"},
                    {"row_id": "row_7"},
                    {"row_id": "row_8", "diagnostics": "Duplicate"},
                ],
            },
            {
                "description": "1 success row (No diagnostics)",
                "rows": [{"row_id": "row_1"}],
            },
        ]

        with patch("update_ack_file.s3_client", s3_client):
            for case in test_cases:
                with self.subTest(msg=case["description"]):
                    # Generate unique file names and set up the S3 file
                    file_info = self.generate_file_names()

                    test_data = {"rows": [{**file_info["row_template"], **row} for row in case["rows"]]}

                    event = self.create_event(test_data)

                    response = lambda_handler(event=event, context={})

                    self.assertEqual(response["statusCode"], 200)
                    self.assertEqual(response["body"], '"Lambda function executed successfully!"')

                    retrieved_object = s3_client.get_object(Bucket=test_bucket_name, Key=file_info["ack_file_name"])
                    actual_ack_file_content = retrieved_object["Body"].read().decode("utf-8")

                    self.create_expected_ack_content(test_data["rows"], actual_ack_file_content, existing_content)

                    mock_firehose_logger.ack_send_log.assert_called()

                    s3_client.delete_object(Bucket=test_bucket_name, Key=file_info["ack_file_name"])

    @patch("log_structure_splunk.firehose_logger")
    def test_lambda_handler_existing(self, mock_firehose_logger):
        """Test lambda handler with dynamic ack_file_name and consistent row_template with an already existing
        ack file with content."""

        os.environ["ACK_BUCKET_NAME"] = DESTINATION_BUCKET_NAME
        existing_content = ValidValues.existing_ack_file_content
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )

        test_cases = [
            {
                "description": "SQS event with multiple errors",
                "rows": [
                    {"row_id": "row_1", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                    {"row_id": "row_2", "diagnostics": "unauthorized"},
                    {"row_id": "row_3", "diagnostics": "not found"},
                ],
            },
            {
                "description": "SQS event with mixed success and failure rows",
                "rows": [
                    {"row_id": "row_4", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                    {"row_id": "row_5"},
                    {"row_id": "row_6"},
                    {"row_id": "row_7", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                    {"row_id": "row_8", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                    {"row_id": "row_9", "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                ],
            },
            {
                "description": "Success rows (No diagnostics)",
                "rows": [{"row_id": "row_412"}, {"row_id": "row_413"}],
            },
        ]

        with patch("update_ack_file.s3_client", s3_client):
            for case in test_cases:
                with self.subTest(msg=case["description"]):
                    # Generate unique file names and set up the S3 file
                    file_info = self.generate_file_names()
                    self.environment_setup(file_info["ack_file_name"], existing_content)

                    test_data = {"rows": [{**file_info["row_template"], **row} for row in case["rows"]]}

                    event = self.create_event(test_data)

                    response = lambda_handler(event=event, context={})

                    self.assertEqual(response["statusCode"], 200)
                    self.assertEqual(response["body"], '"Lambda function executed successfully!"')

                    retrieved_object = s3_client.get_object(
                        Bucket=DESTINATION_BUCKET_NAME, Key=file_info["ack_file_name"]
                    )
                    actual_ack_file_content = retrieved_object["Body"].read().decode("utf-8")

                    self.assertIn(
                        "123^5|OK|Information|OK|30001|Business|30001|Success|20241115T13435500||999^TEST|||True",
                        actual_ack_file_content,
                    )
                    self.assertIn(ValidValues.test_ack_header, actual_ack_file_content)

                    self.create_expected_ack_content(test_data["rows"], actual_ack_file_content, existing_content)

                    mock_firehose_logger.ack_send_log.assert_called()

                    s3_client.delete_object(Bucket=DESTINATION_BUCKET_NAME, Key=file_info["ack_file_name"])

    def test_update_ack_file(self):
        """Test creating ack file with and without diagnostics"""
        self.setup_s3()

        test_cases = [
            {
                "description": "Single successful row",
                "file_key": "COVID19_Vaccinations_v5_YGM41_20240909T13005902.csv",
                "created_at_formatted_string": "20241115T13435500",
                "input_row": [ValidValues.create_ack_data_successful_row],
                "expected_row": [
                    ValidValues.update_ack_file_successful_row_no_immsid,
                ],
            },
            {
                "description": "With multiple rows - failure and success rows",
                "file_key": "COVID19_Vaccinations_v5_YGM41_20240909T13005902.csv",
                "created_at_formatted_string": "20241115T13435500",
                "input_row": [
                    ValidValues.create_ack_data_successful_row,
                    {**ValidValues.create_ack_data_failure_row, "IMMS_ID": "TEST_IMMS_ID"},
                    ValidValues.create_ack_data_failure_row,
                    ValidValues.create_ack_data_failure_row,
                    {**ValidValues.create_ack_data_successful_row, "IMMS_ID": "TEST_IMMS_ID"},
                ],
                "expected_row": [
                    ValidValues.update_ack_file_successful_row_no_immsid,
                    ValidValues.update_ack_file_failure_row_immsid,
                    ValidValues.update_ack_file_failure_row_no_immsid,
                    ValidValues.update_ack_file_failure_row_no_immsid,
                    ValidValues.update_ack_file_successful_row_immsid,
                ],
            },
            {
                "description": "Multiple rows With different diagnostics",
                "file_key": "COVID19_Vaccinations_v5_YGM41_20240909T13005902.csv",
                "created_at_formatted_string": "20241115T13435500",
                "input_row": [
                    {**ValidValues.create_ack_data_failure_row, "OPERATION_OUTCOME": "Error 1"},
                    {**ValidValues.create_ack_data_failure_row, "OPERATION_OUTCOME": "Error 2"},
                    {**ValidValues.create_ack_data_failure_row, "OPERATION_OUTCOME": "Error 3"},
                    {**ValidValues.create_ack_data_failure_row, "OPERATION_OUTCOME": "Error 4"},
                ],
                "expected_row": [
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Error 1"),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Error 2"),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Error 3"),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Error 4"),
                ],
            },
        ]

        with patch("update_ack_file.s3_client", s3_client):
            for case in test_cases:
                with self.subTest(deepcopy(case["description"])):
                    ack_data_rows_with_id = []
                    for row in deepcopy(case["input_row"]):
                        ack_data_rows_with_id.append(row)
                    update_ack_file(case["file_key"], case["created_at_formatted_string"], ack_data_rows_with_id)
                    created_string = case["created_at_formatted_string"]
                    expected_file_key = (
                        f"forwardedFile/{case['file_key'].replace('.csv', f'_BusAck_{created_string}.csv')}"
                    )

                    objects = s3_client.list_objects_v2(Bucket=test_bucket_name)
                    self.assertIn(expected_file_key, [obj["Key"] for obj in objects.get("Contents", [])])
                    retrieved_object = s3_client.get_object(Bucket=test_bucket_name, Key=ack_file_key)
                    retrieved_body = retrieved_object["Body"].read().decode("utf-8")

                    for expected_row in deepcopy(case["expected_row"]):
                        self.assertIn(expected_row, retrieved_body)

                    s3_client.delete_object(Bucket=test_bucket_name, Key=ack_file_key)

    def test_update_ack_file_existing(self):
        """Test appending new rows to an existing ack file."""

        os.environ["ACK_BUCKET_NAME"] = DESTINATION_BUCKET_NAME

        # Mock existing content in the ack file
        existing_content = ValidValues.existing_ack_file_content

        file_key = "RSV_Vaccinations_v5_TEST_20240905T13005922.csv"
        ack_file_key = f"forwardedFile/RSV_Vaccinations_v5_TEST_20240905T13005922_BusAck_20241115T13435500.csv"
        ack_data_rows = [
            ValidValues.create_ack_data_successful_row,
            ValidValues.create_ack_data_failure_row,
        ]

        self.setup_existing_ack_file(DESTINATION_BUCKET_NAME, ack_file_key, existing_content)
        retrieved_object = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)
        retrieved_body = retrieved_object["Body"].read().decode("utf-8")

        with patch("update_ack_file.s3_client", s3_client):
            update_ack_file(file_key, CREATED_AT_FORMATTED_STRING, ack_data_rows)
            retrieved_object = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)
            retrieved_body = retrieved_object["Body"].read().decode("utf-8")

            self.assertIn(
                "123^5|OK|Information|OK|30001|Business|30001|Success|20241115T13435500||999^TEST|||True",
                retrieved_body,
            )

            # Check new rows added to file
            self.assertIn("123^1|OK|", retrieved_body)
            self.assertIn("123^1|Fatal Error|", retrieved_body)

            objects = s3_client.list_objects_v2(Bucket=DESTINATION_BUCKET_NAME)
            self.assertIn(ack_file_key, [obj["Key"] for obj in objects.get("Contents", [])])

            s3_client.delete_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)

    def test_create_ack_data(self):
        """Test create_ack_data with success and failure cases."""

        test_cases = [
            {
                "description": "Success row",
                "created_at_formatted_string": "20241115T13435500",
                "local_id": "local123",
                "row_id": "row456",
                "successful_api_response": True,
                "diagnostics": None,
                "imms_id": "imms789",
                "expected_base": ValidValues.create_ack_data_successful_row,
            },
            {
                "description": "Failure row",
                "created_at_formatted_string": "20241115T13435501",
                "local_id": "local123",
                "row_id": "row456",
                "successful_api_response": False,
                "diagnostics": "Some error occurred",
                "imms_id": "imms789",
                "expected_base": ValidValues.create_ack_data_failure_row,
            },
        ]

        for case in test_cases:
            with self.subTest(case["description"]):
                expected_result = case["expected_base"].copy()
                expected_result.update(
                    {
                        "MESSAGE_HEADER_ID": case["row_id"],
                        "RECEIVED_TIME": case["created_at_formatted_string"],
                        "LOCAL_ID": case["local_id"],
                        "IMMS_ID": case["imms_id"] or "",
                        "OPERATION_OUTCOME": case["diagnostics"] or "",
                    }
                )

                result = create_ack_data(
                    created_at_formatted_string=case["created_at_formatted_string"],
                    local_id=case["local_id"],
                    row_id=case["row_id"],
                    successful_api_response=case["successful_api_response"],
                    diagnostics=case["diagnostics"],
                    imms_id=case["imms_id"],
                )

                self.assertEqual(result, expected_result)

    @mock_s3
    def test_obtain_current_ack_content_file_no_existing(self):
        """Test obtain current ack content when there a file does not already exist."""
        os.environ["ACK_BUCKET_NAME"] = test_bucket_name
        ack_bucket_name = "immunisation-batch-internal-testlambda-data-destinations"
        ACK_KEY = "forwardedFile/COVID19_Vaccinations_v5_YGM41_20240909T13005902_BusAck_20241115T13454555.csv"
        self.setup_s3()
        with patch("update_ack_file.s3_client", s3_client):
            result = obtain_current_ack_content(ack_bucket_name, ACK_KEY)

            self.assertEqual(result.getvalue(), ValidValues.test_ack_header)

    @mock_s3
    def test_obtain_current_ack_content_file_exists(self):
        """Test that the existing ack file content is retrieved and new rows are added."""

        existing_content = ValidValues.existing_ack_file_content
        self.setup_existing_ack_file(DESTINATION_BUCKET_NAME, ack_file_key, existing_content)

        with patch("update_ack_file.s3_client", s3_client):
            result = obtain_current_ack_content(DESTINATION_BUCKET_NAME, ack_file_key)
            self.assertIn(existing_content, result.getvalue())
            self.assertEqual(result.getvalue(), existing_content)

            retrieved_object = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)
            retrieved_body = retrieved_object["Body"].read().decode("utf-8")
            self.assertEqual(retrieved_body, existing_content)

            objects = s3_client.list_objects_v2(Bucket=DESTINATION_BUCKET_NAME)
            self.assertIn(ack_file_key, [obj["Key"] for obj in objects.get("Contents", [])])

            s3_client.delete_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)

    @patch("log_firehose_splunk.FirehoseLogger.ack_send_log")
    @patch("update_ack_file.create_ack_data")
    @patch("update_ack_file.update_ack_file")
    def test_lambda_handler_error_scenarios(self, mock_update_ack_file, mock_create_ack_data, mock_ack_send_log):

        test_cases = [
            {
                "description": "Malformed JSON in SQS body",
                "event": {"Records": [{""}]},
                "expected_message": "Error processing SQS message:",
            },
            {
                "description": "Invalid value in 'diagnostics' field",
                "event": {
                    "Records": [
                        {
                            "body": json.dumps(
                                [
                                    {
                                        "file_key": "test_file.csv",
                                        "row_id": "123",
                                        "local_id": "111^222",
                                        "imms_id": "TEST_IMMS_ID",
                                        "diagnostics": {"unexpected": "object"},
                                        "created_at_formatted_string": "20241212T13000000",
                                    }
                                ]
                            )
                        }
                    ]
                },
                "expected_message": "Error processing SQS message:",
            },
            {
                "description": "Empty Records array in the event",
                "event": {},
                "expected_message": "Error processing SQS message:",
            },
        ]
        mock_update_ack_file.side_effect = Exception("Simulated create_ack_data error")

        for scenario in test_cases:
            with self.subTest(msg=scenario["description"]):
                lambda_handler(event=scenario["event"], context={})

                if scenario["expected_message"]:
                    mock_ack_send_log.assert_called()
                    error_log = mock_ack_send_log.call_args[0][0]
                    self.assertIn(scenario["expected_message"], error_log["event"]["diagnostics"])
                mock_ack_send_log.reset_mock()

    def tearDown(self):
        """'Clear all mock resources"""
        # Clean up mock resources
        os.environ.pop("ACK_BUCKET_NAME", None)


if __name__ == "__main__":
    unittest.main()
