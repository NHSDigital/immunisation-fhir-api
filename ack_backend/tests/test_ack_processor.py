import unittest
from moto import mock_s3, mock_sqs
import os
import json
from boto3 import client as boto3_client
from unittest.mock import patch, MagicMock
from ack_processor import lambda_handler
from update_ack_file import obtain_current_ack_content, create_ack_data, update_ack_file
import boto3
from tests.test_utils_for_ack_backend import DESTINATION_BUCKET_NAME, AWS_REGION, ValidValues, InvalidValues
from constants import Constants
from io import BytesIO, StringIO
from copy import deepcopy
from botocore.exceptions import ClientError
from unittest import TestCase


s3_client = boto3_client("s3", region_name=AWS_REGION)
file_name = "COVID19_Vaccinations_v5_YGM41_20240909T13005902.csv"
ack_file_key = "forwardedFile/COVID19_Vaccinations_v5_YGM41_20240909T13005902_BusAck_20241115T13435500.csv"
local_id = "111^222"
os.environ["ACK_BUCKET_NAME"] = DESTINATION_BUCKET_NAME
invalid_action_flag_diagnostics = "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"


@mock_s3
@mock_sqs
class TestAckProcessorE2E(unittest.TestCase):

    def setup_s3(self):
        """Helper to setup mock S3 buckets and upload test file"""
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )

    def create_event(self, test_data):
        """
        Dynamically create the event for the test with multiple records.
        """
        rows = []
        for test_case_row in test_data["rows"]:
            row = self.row_template.copy()
            row.update(test_case_row)
            rows.append(row)
        print(f"CREATE_EVENT {rows}")
        return {"Records": [{"body": json.dumps(rows)}]}

    row_template = {
        "file_key": file_name,
        "row_id": "123^1",
        "local_id": ValidValues.local_id,
        "action_flag": "create",
        "imms_id": "",
        "created_at_formatted_string": "20241115T13435500",
    }

    @patch("log_structure_splunk.firehose_logger")
    @patch("update_ack_file.s3_client")
    def test_lambda_handler(self, mock_s3_client, mock_firehose_logger):
        """Test lambda handler - No existing Busack file in S3.
        The diagnostics and values for the ack files are created in the record forwarder.
        The information is passed from SQS event to lambda_handler to add to acknowledgement file and splunk
        """

        # Mock empty s3 bucket
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}, "GetObject"
        )

        mock_s3_client.upload_fileobj = MagicMock()

        test_cases = [
            {
                "description": "10 success rows (No diagnostics)",
                "rows": [self.row_template.copy() for row in range(10)],
                "expected_ack_file": [ValidValues.update_ack_file_successful_row_no_immsid for row in range(10)],
            },
            {
                "description": "SQS event with Multiple errors (Multiple diagnostics)",
                "rows": [
                    {
                        **self.row_template.copy(),
                        "diagnostics": invalid_action_flag_diagnostics,
                        "imms_id": "TEST_IMMS_ID",
                    },
                    {**self.row_template.copy(), "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                    {**self.row_template.copy(), "diagnostics": "Validation_error"},
                    {**self.row_template.copy(), "diagnostics": "imms_not_found"},
                ],
                "expected_ack_file": [
                    ValidValues.update_ack_file_failure_row_immsid.replace(
                        "Error_value", invalid_action_flag_diagnostics
                    ),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace(
                        "Error_value", "UNIQUE_ID or UNIQUE_ID_URI is missing"
                    ),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Validation_error"),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "imms_not_found"),
                ],
            },
            {
                "description": "Multiple row processing from SQS event - mixture of success and failure rows",
                "rows": [
                    {**self.row_template.copy(), "imms_id": "TEST_IMMS_ID"},
                    {**self.row_template.copy(), "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"},
                    {**self.row_template.copy(), "diagnostics": "Validation_error"},
                    {**self.row_template.copy()},
                    {**self.row_template.copy(), "diagnostics": "Validation_error", "imms_id": "TEST_IMMS_ID"},
                    {**self.row_template.copy(), "diagnostics": "Validation_error"},
                    {**self.row_template.copy()},
                    {**self.row_template.copy(), "diagnostics": "Duplicate"},
                ],
                "expected_ack_file": [
                    ValidValues.update_ack_file_successful_row_immsid,
                    ValidValues.update_ack_file_failure_row_no_immsid.replace(
                        "Error_value", "UNIQUE_ID or UNIQUE_ID_URI is missing"
                    ),
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Validation_error"),
                    ValidValues.update_ack_file_successful_row_no_immsid,
                    ValidValues.update_ack_file_failure_row_immsid.replace("Error_value", "Validation_error"),
                    ValidValues.update_ack_file_successful_row_no_immsid,
                    ValidValues.update_ack_file_failure_row_no_immsid.replace("Error_value", "Duplicate"),
                ],
            },
            {
                "description": "Multi Line diagnostics",  ### Find example for this
                "rows": [self.row_template.copy()],
                "expected_ack_file": [
                    "123^1|OK|Information|OK|30001|Business|30001|Success|20241115T13435500||default_local_id|||True\n"
                ],
            },
            {
                "description": "Test with updated local_id",
                "rows": [{**self.row_template.copy(), "local_id": "updated_local_id"}],
                "expected_ack_file": [
                    "123^1|OK|Information|OK|30001|Business|30001|Success|20241115T13435500||updated_local_id|||True\n"
                ],
            },
        ]

        # Tests for when there is not an existing Busack file already in S3 bucket
        for case in test_cases:
            with self.subTest(msg=case["description"]):

                event = self.create_event(case)

                response = lambda_handler(event=event, context={})

                self.assertEqual(response["statusCode"], 200)
                self.assertEqual(response["body"], '"Lambda function executed successfully!"')

                uploaded_file_key = mock_s3_client.upload_fileobj.call_args[0][2]

                created_formatted = case["rows"][0]["created_at_formatted_string"]
                expected_file_key = (
                    f"forwardedFile/{case['rows'][0]['file_key'].replace('.csv', f'_BusAck_{created_formatted}.csv')}"
                )
                self.assertEqual(uploaded_file_key, expected_file_key)

                uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue().decode("utf-8")

                for expected_row in case["expected_ack_file"]:
                    self.assertIn(expected_row, uploaded_content)

                mock_firehose_logger.ack_send_log.assert_called()

                mock_s3_client.upload_fileobj.reset_mock()

    @patch("update_ack_file.s3_client")
    def test_update_ack_file(self, mock_s3_client):
        """Test creating ack file with and without diagnostics"""

        # Mock no file already existing in S3 bucket
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}, "GetObject"
        )

        mock_s3_client.upload_fileobj = MagicMock()

        test_cases = [
            {
                "description": "With Diagnostics Single row",
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

        for case in test_cases:
            with self.subTest(deepcopy(case["description"])):
                ack_data_rows_with_id = []
                for row in deepcopy(case["input_row"]):
                    ack_data_rows_with_id.append(row)
                    print("UPDATE ACK TEST")
                update_ack_file(case["file_key"], case["created_at_formatted_string"], ack_data_rows_with_id)
                created_string = case["created_at_formatted_string"]
                expected_file_key = f"forwardedFile/{case['file_key'].replace('.csv', f'_BusAck_{created_string}.csv')}"
                uploaded_file_key = mock_s3_client.upload_fileobj.call_args[0][2]
                print(uploaded_file_key)
                self.assertEqual(
                    uploaded_file_key,
                    expected_file_key,
                )

                uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue().decode("utf-8")
                for expected_row in deepcopy(case["expected_row"]):
                    self.assertIn(expected_row, uploaded_content)

                mock_s3_client.upload_fileobj.reset_mock()

    def tearDown(self):
        # Clean up mock resources
        os.environ.pop("ACK_BUCKET_NAME", None)


if __name__ == "__main__":
    unittest.main()
