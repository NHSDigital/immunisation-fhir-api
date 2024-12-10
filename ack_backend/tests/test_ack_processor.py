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
        """Creates a mock S3 bucket and uploads an existing file with the given content."""
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )

    def setup_existing_ack_file(self, bucket_name, file_key, file_content):
        """Creates a mock S3 bucket and uploads an existing file with the given content."""
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=file_content)

    def create_event(self, test_data):
        """
        Dynamically create the event for the test with multiple records.
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

    def ack_row_order(self, row_input, uploaded_content):
        for row in row_input:
            row_id = row.get("row_id")
            self.assertIn(f"{row_id}|", uploaded_content)

    def create_expected_ack_content(self, row_input, uploaded_content, expected_ack_file_content):
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

        self.assertEqual(uploaded_content, expected_ack_file_content)

        self.ack_row_order(row_input, uploaded_content)

    @patch("log_structure_splunk.firehose_logger")
    @patch("update_ack_file.s3_client")
    def test_lambda_handler(self, mock_s3_client, mock_firehose_logger):
        """Test lambda handler processes file, maintains row order and outputs correct Busackfile content."""

        # Mock empty S3 bucket
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}, "GetObject"
        )
        mock_s3_client.upload_fileobj = MagicMock()

        test_cases = [
            {
                "description": "10 success rows (No diagnostics)",
                "rows": [{**self.row_template.copy(), "row_id": f"row_{i+1}"} for i in range(10)],
            },
            {
                "description": "SQS event with multiple errors",
                "rows": [
                    {
                        **self.row_template.copy(),
                        "row_id": "row_1",
                        "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing",
                    },
                    {**self.row_template.copy(), "row_id": "row_2", "diagnostics": "unauthorized"},
                    {**self.row_template.copy(), "row_id": "row_3", "diagnostics": "not found"},
                ],
            },
            {
                "description": "Multiple row processing from SQS event - mixture of success and failure rows",
                "rows": [
                    {**self.row_template.copy(), "row_id": "row_1", "imms_id": "TEST_IMMS_ID"},
                    {
                        **self.row_template.copy(),
                        "row_id": "row_2",
                        "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing",
                    },
                    {**self.row_template.copy(), "row_id": "row_3", "diagnostics": "Validation_error"},
                    {
                        **self.row_template.copy(),
                        "row_id": "row_4",
                    },
                    {
                        **self.row_template.copy(),
                        "row_id": "row_5",
                        "diagnostics": "Validation_error",
                        "imms_id": "TEST_IMMS_ID",
                    },
                    {**self.row_template.copy(), "row_id": "row_6", "diagnostics": "Validation_error"},
                    {
                        **self.row_template.copy(),
                        "row_id": "row_7",
                    },
                    {**self.row_template.copy(), "row_id": "row_8", "diagnostics": "Duplicate"},
                ],
            },
        ]

        expected_header = ValidValues.test_ack_header

        for case in test_cases:
            with self.subTest(msg=case["description"]):

                event = self.create_event(case)

                response = lambda_handler(event=event, context={})

                self.assertEqual(response["statusCode"], 200)
                self.assertEqual(response["body"], '"Lambda function executed successfully!"')

                # Check correct file has been uploaded
                uploaded_file_key = mock_s3_client.upload_fileobj.call_args[0][2]

                created_formatted = case["rows"][0]["created_at_formatted_string"]
                expected_file_key = (
                    f"forwardedFile/{case['rows'][0]['file_key'].replace('.csv', f'_BusAck_{created_formatted}.csv')}"
                )
                self.assertEqual(uploaded_file_key, expected_file_key)

                uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue().decode("utf-8")

                uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue().decode("utf-8")
                self.assertTrue(uploaded_content.startswith(expected_header))

            expected_ack_file_content = expected_header

            self.create_expected_ack_content(case["rows"], uploaded_content, expected_ack_file_content)

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
                update_ack_file(case["file_key"], case["created_at_formatted_string"], ack_data_rows_with_id)
                created_string = case["created_at_formatted_string"]
                expected_file_key = f"forwardedFile/{case['file_key'].replace('.csv', f'_BusAck_{created_string}.csv')}"
                uploaded_file_key = mock_s3_client.upload_fileobj.call_args[0][2]
                self.assertEqual(
                    uploaded_file_key,
                    expected_file_key,
                )

                uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue().decode("utf-8")

                for expected_row in deepcopy(case["expected_row"]):
                    self.assertIn(expected_row, uploaded_content)

                mock_s3_client.upload_fileobj.reset_mock()

    @patch("update_ack_file.s3_client")
    def test_create_ack_data(self, mock_s3_client):
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

    @patch("update_ack_file.s3_client")
    def test_obtain_current_ack_content_file_not_exists(self, mock_s3_client):
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "GetObject")
        ack_bucket_name = "test-bucket"

        result = obtain_current_ack_content(ack_bucket_name, ack_file_key)
        self.assertEqual(result.getvalue(), ValidValues.test_ack_header)
        mock_s3_client.get_object.assert_called_once_with(Bucket=ack_bucket_name, Key=ack_file_key)
        mock_s3_client.upload_fileobj.reset_mock()

    @mock_s3
    def test_obtain_current_ack_content_file_exists(self):
        """Test that the existing ack file content is retrieved and new rows can be added."""

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
            print("s3 bucket:", [obj["Key"] for obj in objects.get("Contents", [])])

            s3_client.delete_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)

    @patch("update_ack_file.s3_client")
    @patch("update_ack_file.obtain_current_ack_content")
    def test_update_ack_file_existing(self, mock_obtain_current_ack_content, mock_s3_client):
        os.environ["ACK_BUCKET_NAME"] = DESTINATION_BUCKET_NAME

        # Existing file in s3
        existing_content = ValidValues.existing_ack_file_content
        self.setup_existing_ack_file(DESTINATION_BUCKET_NAME, ack_file_key, existing_content)

        mock_obtain_current_ack_content.return_value = StringIO(ValidValues.existing_ack_file_content)
        print(f"EXISTING FILE CONTENT {ValidValues.existing_ack_file_content}")
        file_key = f"RSV_Vaccinations_v5_TEST_20240905T13005922.csv"
        ack_data_rows = [
            ValidValues.create_ack_data_successful_row,
            ValidValues.create_ack_data_failure_row,
        ]

        update_ack_file(file_key, CREATED_AT_FORMATTED_STRING, ack_data_rows)

        expected_key = (
            f"forwardedFile/RSV_Vaccinations_v5_TEST_20240905T13005922_BusAck_{CREATED_AT_FORMATTED_STRING}.csv"
        )

        mock_obtain_current_ack_content.assert_called_once_with(DESTINATION_BUCKET_NAME, expected_key)

        uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue().decode("utf-8")
        print(f"UPLOADED CONTENT: {uploaded_content}")
        self.assertIn("123^5|OK|", uploaded_content)
        self.assertIn("123^1|Fatal Error|", uploaded_content)
        self.assertIn("123^1|OK|", uploaded_content)

    # Lambda handler sqs error scenario
    # The created at formatted date doesn't allow to overwrite the same file, as the created at formatted time is different.
    # test 1 file reuploaded again

    def tearDown(self):
        # Clean up mock resources
        os.environ.pop("ACK_BUCKET_NAME", None)


if __name__ == "__main__":
    unittest.main()
