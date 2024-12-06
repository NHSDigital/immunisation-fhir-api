import unittest
from moto import mock_s3, mock_sqs
import os
import json
from boto3 import client as boto3_client
from unittest.mock import patch, MagicMock
from ack_processor import lambda_handler
from update_ack_file import obtain_current_ack_content, create_ack_data, update_ack_file
import boto3
from tests.test_utils_for_ack_backend import DESTINATION_BUCKET_NAME, AWS_REGION
from constants import Constants
from io import BytesIO


s3_client = boto3_client("s3", region_name=AWS_REGION)
file_name = "COVID19_Vaccinations_v5_YGM41_20240909T13005901.csv"
ack_file_key = "forwardedFile/COVID19_Vaccinations_v5_YGM41_20240909T13005901_BusAck_20241115T13435500.csv"
local_id = "111^222"


@mock_s3
@mock_sqs
class TestAckProcessorE2E(unittest.TestCase):

    def setup_s3(self):
        """Helper to setup mock S3 buckets and upload test file"""
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )

    def invoke_lambda_and_verify_ack(self, event, expected_status, expected_messages):
        """
        Helper method to invoke Lambda and verify acknowledgment file content.
        :param event: The event to pass to the Lambda function
        :param expected_status: Expected HTTP status code in the Lambda response
        :param expected_messages: List of messages expected to be in the acknowledgment file
        """
        # Invoke the Lambda function
        response = lambda_handler(event, context={})
        print(f"event11: {event}")
        # Assert Lambda execution success

        statuses = response["statusCode"]
        print(statuses)
        self.assertEqual(response["statusCode"], expected_status)
        self.assertIn("Lambda function executed successfully", response["body"])

        response = s3_client.list_objects_v2(Bucket=DESTINATION_BUCKET_NAME, Delimiter="/")
        print(f"RESONSE11: {response}")
        # Verify the acknowledgment file in the ack bucket
        ack_file_content = (
            s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=ack_file_key)["Body"].read().decode("utf-8")
        )
        print("MESSAGE11:", expected_messages)
        print(expected_messages)
        # Assert acknowledgment file content
        for message in expected_messages:
            self.assertIn(message, ack_file_content)

    def test_ack_processor_invalid_action_flag(self):
        self.setup_s3()
        event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:create",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": "local_id",
                "operation_requsted": "wrong",
            },
        }
        self.invoke_lambda_and_verify_ack(
            event, 200, ["Fatal Error", "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"]
        )

    def test_ack_processor_imms_not_found(self):
        self.setup_s3()
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "row_id": "855d9cf2-31ef-44ef-8479-8785cf908759^1",
                            "file_key": file_name,
                            "supplier": "EMIS",
                            "created_at_formatted_string": "20241115T13435500",
                            "diagnostics": "Imms id not found",
                            "operation_requested": "update",
                            "local_id": local_id,
                        }
                    )
                }
            ]
        }
        self.invoke_lambda_and_verify_ack(event, 200, ["Fatal Error", "Imms id not found"])

    def test_ack_processor_unique_id_or_uri_missing(self):
        self.setup_s3()
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "row_id": "855d9cf2-31ef-44ef-8479-8785cf908759^1",
                            "file_key": file_name,
                            "supplier": "EMIS",
                            "created_at_formatted_string": "20241115T13435500",
                            "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing",
                            "operation_requested": "",
                            "local_id": local_id,
                        }
                    )
                }
            ]
        }
        self.invoke_lambda_and_verify_ack(event, 200, ["Fatal Error", "UNIQUE_ID or UNIQUE_ID_URI is missing"])

    def test_ack_processor_create_success(self):
        self.setup_s3()
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "statusCode": 201,
                            "headers": {
                                "Location": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/Immunization/719aef39-64b1-4e7b-981e-4acb64e8538e"
                            },
                            "file_key": file_name,
                            "row_id": "6cd75847-e378-451f-984e-b55fa5444b50^1",
                            "created_at_formatted_string": "20241119T11182100",
                            "local_id": "111^222",
                        }
                    )
                }
            ]
        }
        self.invoke_lambda_and_verify_ack(event, 200, ["OK", "719aef39-64b1-4e7b-981e-4acb64e8538e"])

    def test_ack_processor_create_duplicate(self):
        self.setup_s3()
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "statusCode": 422,
                            "headers": {"Content-Type": "application/fhir+json"},
                            "body": json.dumps(
                                {
                                    "resourceType": "OperationOutcome",
                                    "id": "e51e9e59-4d57-41bc-b21f-5ef95547eaac",
                                    "meta": {
                                        "profile": [
                                            "https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"
                                        ]
                                    },
                                    "issue": [
                                        {
                                            "severity": "error",
                                            "code": "duplicate",
                                            "details": {
                                                "coding": [
                                                    {
                                                        "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                                        "code": "DUPLICATE",
                                                    }
                                                ]
                                            },
                                            "diagnostics": (
                                                "The provided identifier: https://www.ravs.england.nhs.uk/#0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057 is duplicated"
                                            ),
                                        }
                                    ],
                                }
                            ),
                            "file_key": file_name,
                            "row_id": "8fb764cf-93af-453f-9246-ea6cd6244069^1",
                            "created_at_formatted_string": "20241119T11554300",
                        }
                    )
                }
            ]
        }
        self.invoke_lambda_and_verify_ack(
            event,
            200,
            [
                "Fatal Error",
                "The provided identifier: https://www.ravs.england.nhs.uk/#0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057 is duplicated",
            ],
        )

    def test_ack_processor_update_and_delete_success(self):
        self.setup_s3()
        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "statusCode": 200,
                            "headers": {},
                            "file_key": file_name,
                            "row_id": "565d8c47-25ee-4958-a59b-3a4fc0e8c6da^1",
                            "created_at_formatted_string": "20241119T11344900",
                            "local_id": local_id,
                        }
                    )
                }
            ]
        }
        self.invoke_lambda_and_verify_ack(event, 200, ["OK"])

    def test_obtain_current_ack_content(self):
        """Test obtaining ack content when ack file does not already exist."""
        self.setup_s3()

        file_key = "test_file.csv"
        created_at_formatted_string = "20211115T13435500"
        ack_bucket_name = DESTINATION_BUCKET_NAME

        result = obtain_current_ack_content(
            ack_bucket_name, f"forwardedFile{file_key}_BusAck_{created_at_formatted_string}.csv"
        )

        # Get the file content
        file_content = result.getvalue().strip()

        expected_headers = "|".join(Constants.ack_headers)

        # Assert the headers are correctly generated
        self.assertEqual(file_content, expected_headers)

    @patch("update_ack_file.s3_client")
    def test_obtain_current_ack_content_existing_file(self, mock_s3_client):
        """Test obtaining ack content when an existing file is present in S3."""
        self.setup_s3()

        ack_bucket_name = DESTINATION_BUCKET_NAME
        existing_file_content = (
            "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
            "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|"
            "IMMS_ID|OPERATION_OUTCOME|MESSAGE_DELIVERY|\n"
            "12345|OK|Information|OK|30001|Business|30001|Success|20241125T17143300"
            "|mock_mailbox|local_123|imms_456||True"
        )

        existing_file_content_bytes = existing_file_content.encode("utf-8")
        mock_s3_client.list_objects_v2.return_value = {"Contents": [{"Key": f"{ack_file_key}"}]}
        mock_s3_client.get_object.return_value = {"Body": BytesIO(existing_file_content_bytes)}

        result = obtain_current_ack_content(ack_bucket_name, ack_file_key)

        file_content = result.getvalue().strip()
        existing_file_content_str = existing_file_content_bytes.decode("utf-8").strip()

        self.assertEqual(file_content, existing_file_content_str)
        mock_s3_client.get_object.assert_called_once_with(Bucket=ack_bucket_name, Key=ack_file_key)

    @patch("update_ack_file.s3_client")
    def test_update_new_file(self, mock_s3_client):
        """Test obtaining ack content when an existing file is present in S3."""
        self.setup_s3()

        ack_bucket_name = DESTINATION_BUCKET_NAME
        existing_file_content = (
            "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
            "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|"
            "IMMS_ID|OPERATION_OUTCOME|MESSAGE_DELIVERY|\n"
            "12345|OK|Information|OK|30001|Business|30001|Success|20241125T17143300"
            "|mock_mailbox|local_123|imms_456||True"
        )

        existing_file_content_bytes = existing_file_content.encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": BytesIO(existing_file_content_bytes)}

        result = obtain_current_ack_content(ack_bucket_name, ack_file_key)

        file_content = result.getvalue().strip()
        existing_file_content_str = existing_file_content_bytes.decode("utf-8").strip()
        # print("result:", existing_file_content_str)

        self.assertEqual(file_content, existing_file_content_str)
        mock_s3_client.get_object.assert_called_once_with(Bucket=ack_bucket_name, Key=ack_file_key)

    def test_create_ack_data(self):
        created_at_formatted_string = "20241015T18504900"
        row_id = "test_file_id^1"

        success_ack_data = {
            "MESSAGE_HEADER_ID": row_id,
            "HEADER_RESPONSE_CODE": "OK",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "30001",
            "RESPONSE_TYPE": "Business",
            "RESPONSE_CODE": "30001",
            "RESPONSE_DISPLAY": "Success",
            "RECEIVED_TIME": created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": local_id,
            "IMMS_ID": "test_imms_id",
            "OPERATION_OUTCOME": "",
            "MESSAGE_DELIVERY": True,
        }

        failure_ack_data = {
            "MESSAGE_HEADER_ID": row_id,
            "HEADER_RESPONSE_CODE": "Fatal Error",
            "ISSUE_SEVERITY": "Fatal",
            "ISSUE_CODE": "Fatal Error",
            "ISSUE_DETAILS_CODE": "30002",
            "RESPONSE_TYPE": "Business",
            "RESPONSE_CODE": "30002",
            "RESPONSE_DISPLAY": "Business Level Response Value - Processing Error",
            "RECEIVED_TIME": created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": local_id,
            "IMMS_ID": "",
            "OPERATION_OUTCOME": "Some diagnostics",
            "MESSAGE_DELIVERY": False,
        }

        # Test case tuples are structured as (test_name, successful_api_response, diagnostics, imms_id, expected output)
        test_cases = [
            ("ack data for success", True, None, "test_imms_id", success_ack_data),
            ("ack data for failure", False, "Some diagnostics", "", failure_ack_data),
        ]

        for test_name, successful_api_response, diagnostics, imms_id, expected_output in test_cases:
            with self.subTest(test_name):
                self.assertEqual(
                    create_ack_data(
                        created_at_formatted_string, local_id, row_id, successful_api_response, diagnostics, imms_id
                    ),
                    expected_output,
                )
                print(f"EXPETECED 111:{expected_output}")

    @patch("update_ack_file.s3_client")
    def test_update_ack_file(self, mock_s3_client):
        """Test updating the ack file with and without diagnostics."""
        ack_bucket_name = "test-bucket"
        os.environ["ACK_BUCKET_NAME"] = ack_bucket_name

        existing_content = (
            "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|ISSUE_DETAILS_CODE|RESPONSE_TYPE|"
            "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|"
            "IMMS_ID|OPERATION_OUTCOME|MESSAGE_DELIVERY|\n"
            "12345|OK|Information|OK|30001|Business|30001|Success|20241125T17143300"
            "|mock_mailbox|local_123|imms_456||True\n"
        )

        existing_file_content_bytes = existing_content.encode("utf-8")

        mock_s3_client.get_object.return_value = {"Body": BytesIO(existing_file_content_bytes)}
        mock_s3_client.upload_fileobj = MagicMock()

        # Test cases
        test_cases = [
            {
                "description": "With Diagnostics",
                "file_key": "test_file.csv",
                "local_id": "111^222",
                "row_id": "row123",
                "successful_api_response": False,
                "diagnostics": "An error occurred while processing the request",
                "imms_id": "imms123",
                "created_at_formatted_string": "20241115T13435500",
                "operation_outcome": "create",
                "expected_row": (
                    "row123|Fatal Error|Fatal|Fatal Error|30002|Business|30002|"
                    "Business Level Response Value - Processing Error|20241115T13435500|||"
                    "111^222|imms456|An error occurred while processing the request|False\n"
                ),
            },
            {
                "description": "Without Diagnostics",
                "file_key": "test_file.csv",
                "local_id": "111^222",
                "row_id": "row123",
                "successful_api_response": True,
                "diagnostics": None,
                "imms_id": "imms456",
                "created_at_formatted_string": "20241115T13435500",
                "operation_outcome": "create",
                "expected_row": (
                    "row123|OK|Information|OK|30001|Business|30001|Success|"
                    "20241115T13435500|||111^222|imms456||True\n"
                ),
            },
        ]

        for case in test_cases:
            with self.subTest(case["description"]):
                update_ack_file(case["file_key"], case["created_at_formatted_string"], case["expected_row"])
                mock_s3_client.upload_fileobj.assert_called_once()
                uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0].getvalue()
                print(f"UPLOADED CONTENT {uploaded_content}")
                self.assertIn(case["expected_row"], uploaded_content)

                mock_s3_client.upload_fileobj.reset_mock()

    def tearDown(self):
        # Clean up mock resources
        os.environ.pop("ACK_BUCKET_NAME", None)
