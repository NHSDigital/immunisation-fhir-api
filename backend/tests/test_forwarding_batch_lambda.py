import base64
import copy
import json
import os
import unittest
from typing import Optional
from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

from boto3 import resource as boto3_resource
from models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    MessageNotSuccessfulError,
    RecordProcessorError,
    ResourceFoundError,
    ResourceNotFoundError,
)
from moto import mock_aws
from utils.test_utils_for_batch import ForwarderValues, MockFhirImmsResources

with patch.dict("os.environ", ForwarderValues.MOCK_ENVIRONMENT_DICT):
    from forwarding_batch_lambda import (
        create_diagnostics_dictionary,
        forward_lambda_handler,
    )


@mock_aws
@patch.dict(os.environ, ForwarderValues.MOCK_ENVIRONMENT_DICT)
class TestForwardLambdaHandler(TestCase):
    def setUp(self):
        """Set up dynamodb table test values to be used for the tests"""
        self.dynamodb_resource = boto3_resource("dynamodb", "eu-west-2")
        self.table = self.dynamodb_resource.create_table(
            TableName="immunisation-batch-internal-dev-imms-test-table",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "PatientPK", "AttributeType": "S"},
                {"AttributeName": "IdentifierPK", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "IdentifierGSI",
                    "KeySchema": [{"AttributeName": "IdentifierPK", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
                {
                    "IndexName": "PatientGSI",
                    "KeySchema": [
                        {"AttributeName": "PatientPK", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
            ],
        )
        self.redis_patcher = patch("models.utils.validation_utils.redis_client")
        self.mock_redis_client = self.redis_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

    def tearDown(self):
        """Tear down after each test. This runs after every test"""
        patch.stopall()

    @staticmethod
    def generate_fhir_json(include_fhir_json=True, identifier_value=None, operation_requested="CREATE"):
        """Generates the fhir json for cases where included and None if excluded"""
        if not include_fhir_json:
            return None

        fhir_json = (
            copy.deepcopy(MockFhirImmsResources.all_fields)
            if operation_requested != "DELETE"
            else (copy.deepcopy(MockFhirImmsResources.delete_operation_fields))
        )

        if fhir_json.get("identifier") and identifier_value is not None:
            fhir_json["identifier"][0]["value"] = identifier_value

        return fhir_json

    @staticmethod
    def generate_details_from_processing(
        include_fhir_json=True, operation_requested="CREATE", local_id="local-1", identifier_value=None
    ):
        """Helper to generate details_from_processing for row data."""
        details = {
            "operation_requested": operation_requested,
            "local_id": local_id,
        }
        if include_fhir_json:
            details["fhir_json"] = TestForwardLambdaHandler.generate_fhir_json(
                include_fhir_json, identifier_value, operation_requested
            )
        return details

    @staticmethod
    def generate_input(
        row_id: int,
        identifier_value: Optional[str] = None,
        file_key: str = "test_file_key",
        created_at_formatted_string: str = "2025-01-24T12:00:00Z",
        include_fhir_json: bool = True,
        operation_requested: str = "create",
        diagnostics: dict = None,
        supplier: str = "test_supplier",
    ):
        """Generates input rows for test_cases."""
        details_from_processing = TestForwardLambdaHandler.generate_details_from_processing(
            include_fhir_json=include_fhir_json,
            operation_requested=operation_requested,
            local_id=f"local-{row_id}",
            identifier_value=identifier_value,
        )
        row = {
            "row_id": f"row-{row_id}",
            "file_key": file_key,
            "created_at_formatted_string": created_at_formatted_string,
            "supplier": supplier,
            "vax_type": "RSV",
            **details_from_processing,
        }
        if diagnostics:
            row["diagnostics"] = diagnostics
        return row

    @staticmethod
    def generate_event(test_cases):
        """Generates a kinesis event from test_cases."""
        records = []
        for case in test_cases:
            message_body = case["input"]
            encoded_body = base64.b64encode(json.dumps(message_body).encode("utf-8")).decode("utf-8")
            records.append({"kinesis": {"data": encoded_body}})
        return {"Records": records}

    def assert_values_in_sqs_messages(self, mock_send_message, test_cases):
        """Assert keys and values are found in SQS messages."""

        sqs_messages = [json.loads(call[1]["MessageBody"]) for call in mock_send_message.call_args_list]

        sqs_messages = sqs_messages[0] if len(sqs_messages) == 1 and isinstance(sqs_messages[0], list) else sqs_messages

        for idx, test_case in enumerate(test_cases):
            expected_keys = test_case["expected_keys"]
            expected_values = test_case["expected_values"]

            with self.subTest(test_case=test_case["name"]):
                for key in expected_keys:
                    assert key in sqs_messages[idx]

                message = sqs_messages[idx]
                for key, value in expected_values.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            assert message[key][sub_key] == sub_value

                    else:
                        assert message[key] == value

    def assert_dynamo_item(self, expected_dynamo_item):
        """Asserts whether expected values are returned in mock_dynamodb table"""
        table_items = self.table.scan()["Items"]
        match_found = False

        if expected_dynamo_item is None:
            self.assertFalse(match_found)
        else:
            for item in table_items:
                if all(item.get(k) == v for k, v in expected_dynamo_item.items()):
                    match_found = True

            self.assertTrue(match_found)

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    def test_forward_lambda_handler_single_operations(self, mock_send_message):
        """Test each operation independently in forward lambda handler.
        name: Description of the test case scenario,
        input: generates the kinesis row data for the event,
        expected_keys (list): expected output dictionary keys,
        expected_values (dict): expected output dictionary values
        All records are for the same file"""
        pk_test = "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c"
        table_item = copy.deepcopy(ForwarderValues.EXPECTED_TABLE_ITEM)
        table_item.update(
            {
                "PK": pk_test,
                "IdentifierPK": "https://www.ravs.england.nhs.uk/#RSV_002",
                "PatientSK": "RSV#4d2ac1eb-080f-4e54-9598-f2d53334681c",
            }
        )
        self.mock_redis_client.hget.return_value = "RSV"

        test_cases = [
            {
                "name": "Single Create Success",
                "input": self.generate_input(
                    row_id=1,
                    operation_requested="CREATE",
                    include_fhir_json=True,
                    identifier_value="single_test_create",
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-1", **ForwarderValues.EXPECTED_VALUES},
                "expected_dynamo_item": {
                    "IdentifierPK": "https://www.ravs.england.nhs.uk/#single_test_create",
                    "Operation": "CREATE",
                },
            },
            {
                "name": "Single Update Success",
                "input": self.generate_input(row_id=1, operation_requested="UPDATE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-1", "imms_id": pk_test, **ForwarderValues.EXPECTED_VALUES},
                "expected_dynamo_item": table_item,
            },
            {
                "name": "Single Delete Success",
                "input": self.generate_input(row_id=1, operation_requested="DELETE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {
                    "row_id": "row-1",
                    "imms_id": pk_test,
                    "operation_requested": "DELETE",
                    **ForwarderValues.EXPECTED_VALUES,
                },
                "expected_dynamo_item": {
                    "PK": "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                    "PatientPK": "Patient#9177036360",
                    "IdentifierPK": "https://www.ravs.england.nhs.uk/#RSV_002",
                    "Operation": "DELETE",
                },
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                mock_send_message.reset_mock()
                self.table.put_item(
                    Item={
                        "PK": pk_test,
                        "PatientPK": "Patient#9177036360",
                        "IdentifierPK": "https://www.ravs.england.nhs.uk/#RSV_002",
                        "Version": 1,
                    }
                )
                event = self.generate_event([test_case])
                forward_lambda_handler(event, {})
                self.assert_values_in_sqs_messages(mock_send_message, [test_case])
                self.assert_dynamo_item(test_case["expected_dynamo_item"])

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    def test_forward_lambda_handler_multiple_scenarios(self, mock_send_message):
        """Test forward lambda handler with multiple rows in the event with create, update, and delete operations,
        and diagnostics handling.
            name: Description of the test case scenario,
            input: generates the kinesis row data for the event,
            expected_keys (list): expected output dictionary keys,
            expected_values (dict): expected output dictionary values
        Based on a maximum 10 rows received in event for the same file at a time to the forward_lambda_handler.
        All records are for the same file"""

        table_item = copy.deepcopy(ForwarderValues.EXPECTED_TABLE_ITEM)
        table_item.update(
            {
                "PK": "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                "IdentifierPK": "https://www.ravs.england.nhs.uk/#RSV_002",
                "PatientSK": "RSV#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                "Operation": "DELETE",
            }
        )

        test_cases = [
            {
                "name": "Row 1: Create Success",
                "input": self.generate_input(
                    row_id=1, operation_requested="CREATE", include_fhir_json=True, identifier_value="RSV_CREATE"
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-1", **ForwarderValues.EXPECTED_VALUES},
            },
            {
                "name": "Row 2: Duplication Error: Create failure ",
                "input": self.generate_input(row_id=2, operation_requested="CREATE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-2",
                    "diagnostics": create_diagnostics_dictionary(
                        IdentifierDuplicationError("https://www.ravs.england.nhs.uk/#RSV_002")
                    ),
                },
            },
            {
                "name": "Row 3: Update success",
                "input": self.generate_input(row_id=3, operation_requested="UPDATE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-3", "imms_id": "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c"},
            },
            {
                "name": "Row 4: Update failure",
                "input": self.generate_input(
                    row_id=4, operation_requested="UPDATE", include_fhir_json=True, identifier_value="RSV_UPDATE"
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-4",
                    "diagnostics": create_diagnostics_dictionary(
                        ResourceNotFoundError(
                            resource_type="Immunization", resource_id="https://www.ravs.england.nhs.uk/#RSV_UPDATE"
                        )
                    ),
                },
            },
            {
                "name": "Row 5: Delete Success",
                "input": self.generate_input(row_id=5, operation_requested="DELETE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-5", "imms_id": "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c"},
            },
            {
                "name": "Row 6: Delete Failure",
                "input": self.generate_input(row_id=6, operation_requested="DELETE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-6",
                    "diagnostics": create_diagnostics_dictionary(
                        ResourceNotFoundError(
                            resource_type="Immunization",
                            resource_id="Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                        )
                    ),
                },
            },
            {
                "name": "Row 7: Diagnostics Already Present",
                "input": self.generate_input(
                    row_id=7,
                    operation_requested="CREATE",
                    include_fhir_json=True,
                    diagnostics=create_diagnostics_dictionary(MessageNotSuccessfulError("Unable to reach API")),
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-7",
                    "diagnostics": create_diagnostics_dictionary(MessageNotSuccessfulError("Unable to reach API")),
                },
            },
            {
                "name": "Row 8: Delete Failure",
                "input": self.generate_input(row_id=8, operation_requested="DELETE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-8",
                    "diagnostics": create_diagnostics_dictionary(
                        ResourceNotFoundError(
                            resource_type="Immunization",
                            resource_id="Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                        )
                    ),
                },
            },
            {
                "name": "Row 9: FHIR_JSON does not exist",
                "input": self.generate_input(row_id=9, operation_requested="UPDATE", include_fhir_json=False),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-9",
                    "diagnostics": create_diagnostics_dictionary(
                        MessageNotSuccessfulError("Server error - FHIR JSON not correctly sent to forwarder")
                    ),
                },
            },
            {
                "name": "Row 10: Validation error exists from record processor",
                "input": self.generate_input(
                    row_id=10,
                    operation_requested="UPDATE",
                    diagnostics=create_diagnostics_dictionary(
                        CustomValidationError("An error from the record processor")
                    ),
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-10",
                    "diagnostics": create_diagnostics_dictionary(
                        CustomValidationError("An error from the record processor")
                    ),
                },
            },
        ]

        self.table.put_item(
            Item={
                "PK": "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                "PatientPK": "Patient#9732928395",  # 9177036360",
                "PatientSK": "RSV#4d2ac1eb-080f-4e54-9598-f2d53334681c",
                "IdentifierPK": "https://www.ravs.england.nhs.uk/#RSV_002",
                "Version": 1,
            }
        )
        mock_send_message.reset_mock()
        event = self.generate_event(test_cases)

        self.mock_redis_client.hget.return_value = "RSV"
        forward_lambda_handler(event, {})

        self.assert_dynamo_item(table_item)
        self.assert_values_in_sqs_messages(mock_send_message, test_cases)

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    def test_forward_lambda_handler_groups_and_sends_events_by_filename(self, mock_send_message):
        """VED-734 - each batch handled by the Lambda may have events relating to different parent CSV files. This
        test ensures events are grouped accordingly and sent with the correct SQS"""
        mock_records = [
            {
                "input": self.generate_input(
                    row_id=1,
                    identifier_value="supplier_1_system/54321",
                    operation_requested="CREATE",
                    file_key="supplier_1_rsv_test_file",
                    supplier="supplier_1",
                )
            },
            {
                "input": self.generate_input(
                    row_id=2,
                    identifier_value="supplier_2_system/12345",
                    operation_requested="CREATE",
                    file_key="supplier_2_rsv_test_file",
                    supplier="supplier_2",
                )
            },
        ]
        mock_kinesis_event = self.generate_event(mock_records)
        self.mock_redis_client.hget.return_value = "RSV"

        forward_lambda_handler(mock_kinesis_event, {})

        sqs_calls = mock_send_message.call_args_list
        _, first_call_kwargs = sqs_calls[0]
        _, second_call_kwargs = sqs_calls[1]

        # Separate calls are made for each of the respective groups
        self.assertEqual(len(sqs_calls), 2)
        self.assertEqual(first_call_kwargs["MessageGroupId"], "supplier_1_rsv_test_file_2025-01-24T12:00:00Z")
        self.assertEqual(second_call_kwargs["MessageGroupId"], "supplier_2_rsv_test_file_2025-01-24T12:00:00Z")

        self.assertDictEqual(
            json.loads(first_call_kwargs["MessageBody"])[0],
            {
                "created_at_formatted_string": "2025-01-24T12:00:00Z",
                "file_key": "supplier_1_rsv_test_file",
                "operation_start_time": ANY,
                "operation_end_time": ANY,
                "imms_id": ANY,
                "local_id": "local-1",
                "operation_requested": "CREATE",
                "row_id": "row-1",
                "supplier": "supplier_1",
                "vaccine_type": "RSV",
            },
        )
        self.assertDictEqual(
            json.loads(second_call_kwargs["MessageBody"])[0],
            {
                "created_at_formatted_string": "2025-01-24T12:00:00Z",
                "file_key": "supplier_2_rsv_test_file",
                "operation_start_time": ANY,
                "operation_end_time": ANY,
                "imms_id": ANY,
                "local_id": "local-2",
                "operation_requested": "CREATE",
                "row_id": "row-2",
                "supplier": "supplier_2",
                "vaccine_type": "RSV",
            },
        )

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    def test_forward_lambda_handler_update_scenarios(self, mock_send_message):
        """Test forward lambda handler with multiple rows in the event with update and delete operations,
        to test update scenarios.
            name: Description of the test case scenario,
            input: generates the kinesis row data for the event,
            expected_keys (list): expected output dictionary keys,
            expected_values (dict): expected output dictionary values"""
        self.mock_redis_client.hget.return_value = "RSV"
        pk_test_update = "Immunization#4d2ac1eb-080f-4e54-9598-f2d53334687r"
        self.table.put_item(
            Item={
                "PK": pk_test_update,
                "PatientPK": "Patient#9177036360",
                "IdentifierPK": "https://www.ravs.england.nhs.uk/#UPDATE_TEST",
                "Version": 1,
            }
        )

        test_cases = [
            {
                "name": "Row 1a: Update existing record",
                "input": self.generate_input(
                    row_id=1, operation_requested="UPDATE", include_fhir_json=True, identifier_value="UPDATE_TEST"
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-1", "imms_id": pk_test_update},
                "expected_table_item": {
                    "PK": pk_test_update,
                    "PatientPK": "Patient#9732928395",
                },
                "expected_dynamo_item": {
                    "PK": pk_test_update,
                    **ForwarderValues.EXPECTED_TABLE_ITEM,
                },
            },
            {
                "name": "Row 2a: Delete the updated record",
                "input": self.generate_input(
                    row_id=2, operation_requested="DELETE", include_fhir_json=True, identifier_value="UPDATE_TEST"
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-2", "imms_id": pk_test_update},
                "expected_table_item": {
                    "PK": pk_test_update,
                    "PatientPK": "Patient#9732928395",
                },
                "expected_dynamo_item": {
                    "PK": pk_test_update,
                    "Operation": "DELETE",
                },
            },
            {
                "name": "Row 3a: Delete Error to Confirm record does not exist anymore",
                "input": self.generate_input(
                    row_id=3, operation_requested="DELETE", include_fhir_json=True, identifier_value="UPDATE_TEST"
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS_DIAGNOSTICS,
                "expected_values": {
                    "row_id": "row-3",
                    "diagnostics": create_diagnostics_dictionary(
                        ResourceNotFoundError(
                            resource_type="Immunization",
                            resource_id="Immunization#4d2ac1eb-080f-4e54-9598-f2d53334687r",
                        )
                    ),
                },
                "expected_dynamo_item": None,
            },
            {
                "name": "Row 4a: Reinstated record using Update operation",
                "input": self.generate_input(
                    row_id=4, operation_requested="UPDATE", include_fhir_json=True, identifier_value="UPDATE_TEST"
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-4", "imms_id": pk_test_update},
                "expected_dynamo_item": {
                    "PK": pk_test_update,
                    **ForwarderValues.EXPECTED_TABLE_ITEM_REINSTATED,
                },
            },
            {
                "name": "Row 5a: Updating a Reinstated record - created_at_formatted string amended for test",
                "input": self.generate_input(
                    row_id=5,
                    operation_requested="UPDATE",
                    include_fhir_json=True,
                    identifier_value="UPDATE_TEST",
                    created_at_formatted_string="2025-05-24T12:22:00Z",
                ),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {"row_id": "row-5", "imms_id": pk_test_update},
                "expected_dynamo_item": {
                    "PK": pk_test_update,
                    **ForwarderValues.EXPECTED_TABLE_ITEM_REINSTATED,
                },
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                mock_send_message.reset_mock()
                event = self.generate_event([test_case])
                forward_lambda_handler(event, {})
                self.assert_values_in_sqs_messages(mock_send_message, [test_case])
                self.assert_dynamo_item(test_case["expected_dynamo_item"])

    def test_create_diagnostics_dictionary(self):
        """Tests diagnostics dictionary returns the correct output"""

        test_cases = [
            {
                "error": RecordProcessorError("Diagnostics from recordprocessor"),
                "expected_output": "Diagnostics from recordprocessor",
            },
            {
                "error": CustomValidationError("Validation failed"),
                "expected_output": {
                    "error_type": "CustomValidationError",
                    "statusCode": 400,
                    "error_message": "Validation failed",
                },
            },
            {
                "error": IdentifierDuplicationError("Duplicate identifier"),
                "expected_output": {
                    "error_type": "IdentifierDuplicationError",
                    "statusCode": 422,
                    "error_message": "The provided identifier: Duplicate identifier is duplicated",
                },
            },
            {
                "error": ResourceNotFoundError(resource_type="Immunization", resource_id=None),
                "expected_output": {
                    "error_type": "ResourceNotFoundError",
                    "statusCode": 404,
                    "error_message": "Immunization resource does not exist. ID: None",
                },
            },
            {
                "error": ResourceFoundError(resource_type="Immunization", resource_id="A-primary-key"),
                "expected_output": {
                    "error_type": "ResourceFoundError",
                    "statusCode": 409,
                    "error_message": "Immunization resource does exist. ID: A-primary-key",
                },
            },
            {
                "error": MessageNotSuccessfulError("Message processing failed"),
                "expected_output": {
                    "error_type": "MessageNotSuccessfulError",
                    "statusCode": 500,
                    "error_message": "Message processing failed",
                },
            },
            {
                "error": Exception("General exception"),
                "expected_output": {
                    "error_type": "Exception",
                    "statusCode": 500,
                    "error_message": "General exception",
                },
            },
        ]

        for case in test_cases:
            with self.subTest(error=case["error"]):
                result = create_diagnostics_dictionary(case["error"])
                self.assertEqual(result, case["expected_output"])

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    @patch("forwarding_batch_lambda.forward_request_to_dynamo")
    @patch("forwarding_batch_lambda.create_table")
    @patch("forwarding_batch_lambda.make_batch_controller")
    def test_forward_request_to_dynamo(
        self, mock_make_controller, mock_create_table, mock_forward_request_to_dynamo, mock_send_message
    ):
        """Test forward lambda handler to assert dynamo db is called,
        and diagnostics handling.
            name: Description of the test case scenario,
            input: generates the kinesis row data for the event,
            expected_keys (list): expected output dictionary keys,
            expected_values (dict): expected output dictionary values
        """
        mock_create_table.return_value = {}
        mock_make_controller.return_value = MagicMock()
        mock_forward_request_to_dynamo.side_effect = [
            "IMMS123",
        ]

        test_case = [
            {
                "name": "Row 1: Create Success",
                "input": self.generate_input(row_id=1, operation_requested="CREATE", include_fhir_json=True),
                "expected_keys": ForwarderValues.EXPECTED_KEYS,
                "expected_values": {
                    "row_id": "row-1",
                    "file_key": "test_file_key",
                    "created_at_formatted_string": "2025-01-24T12:00:00Z",
                    "supplier": "test_supplier",
                    "vax_type": "RSV",
                    "local_id": "local-1",
                    "operation_requested": "CREATE",
                },
            },
        ]

        event = self.generate_event(test_case)

        forward_lambda_handler(event, {})

        call = mock_forward_request_to_dynamo.call_args_list
        call_data = call[0][0][0]
        expected_values = test_case[0]["expected_values"]
        assert expected_values.items() <= call_data.items()

    def clear_test_tables(self):
        """Clear DynamoDB table after each test."""
        scan = self.table.scan()
        items = scan.get("Items", [])
        while items:
            for item in items:
                self.table.delete_item(Key={"PK": item["PK"]})
            scan = self.table.scan()
            items = scan.get("Items", [])

    def teardown(self):
        """Deletes mock dynamodb resource"""
        self.table.delete()
        self.dynamodb_resource = None


if __name__ == "__main__":
    unittest.main()
