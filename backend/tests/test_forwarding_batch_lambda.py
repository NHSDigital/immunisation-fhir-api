import unittest
from unittest import TestCase
from unittest.mock import patch, MagicMock
from forwarding_batch_lambda import forward_lambda_handler, create_diagnostics_dictionary
from models.errors import (
    MessageNotSuccessfulError,
    RecordProcessorError,
    CustomValidationError,
    IdentifierDuplicationError,
    ResourceNotFoundError,
    ResourceFoundError,
)
import base64
import json
from tests.utils.test_utils_for_batch import ForwarderValues


class TestForwardLambdaHandler(TestCase):

    @staticmethod
    def generate_fhir_json(include_fhir_json=True):
        """Generates the fhir json for cases where included and None if excluded"""
        if include_fhir_json:
            return ForwarderValues.mandatory_fields_only
        return None

    @staticmethod
    def generate_details_from_processing(include_fhir_json=True, operation_requested="create", local_id="local-1"):
        """Helper to generate details_from_processing for row data."""
        details = {
            "operation_requested": operation_requested,
            "local_id": local_id,
        }
        if include_fhir_json:
            details["fhir_json"] = TestForwardLambdaHandler.generate_fhir_json(include_fhir_json)
        return details

    @staticmethod
    def generate_input(
        row_id,
        file_key="test_file_key",
        created_at_formatted_string="2025-01-24T12:00:00Z",
        include_fhir_json=True,
        operation_requested="create",
        diagnostics=None,
    ):
        """Generates input rows for test_cases."""
        details_from_processing = TestForwardLambdaHandler.generate_details_from_processing(
            include_fhir_json=include_fhir_json, operation_requested=operation_requested, local_id=f"local-{row_id}"
        )
        row = {
            "row_id": f"row-{row_id}",
            "file_key": file_key,
            "created_at_formatted_string": created_at_formatted_string,
            "supplier": "test_supplier",
            "vax_type": "COVID19",
            **details_from_processing,
        }
        if diagnostics:
            row["diagnostics"] = diagnostics
        return row

    @staticmethod
    def generate_event(test_cases):
        """Generates an event from test_cases."""
        records = []
        for case in test_cases:
            message_body = case["input"]
            encoded_body = base64.b64encode(json.dumps(message_body).encode("utf-8")).decode("utf-8")
            records.append({"kinesis": {"data": encoded_body}})
        return {"Records": records}

    def assert_values_in_sqs_messages(self, mock_send_message, test_cases):
        """Assert keys are found in SQS messages."""

        sqs_messages = [json.loads(call[1]["MessageBody"]) for call in mock_send_message.call_args_list]
        # Flatten the list if necessary
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

    def assert_forward_request_to_dynamo(self, mock_forward_request_to_dynamo, test_cases):
        """Helper to assert forward_request_to_dynamo invocations."""

        for i, (test_case, call) in enumerate(zip(test_cases, mock_forward_request_to_dynamo.call_args_list)):
            expected_row = test_case["input"]
            call_data = call[0]

            with self.subTest(test_case=test_case["name"]):

                required_keys = ["row_id", "file_key", "created_at_formatted_string", "local_id", "fhir_json"]

                for key in required_keys:
                    assert key in call_data[0]
                    assert call_data[0][key] == expected_row[key], f"{key} does not match in call {i+1}"

    def total_forward_request_to_dynamo(self, mock_forward_request_to_dynamo, test_cases):
        """Asserts number of forward_request_to_dynamo invocations matches number of rows in test_case"""
        assert len(mock_forward_request_to_dynamo.call_args_list) == len(
            test_cases
        ), f"Expected {len(test_cases)} calls, but got {len(mock_forward_request_to_dynamo.call_args_list)}"

        # Ensure the total number of invocations matches the expected counts for each operation
        create_calls = sum(1 for case in test_cases if case["input"]["operation_requested"] == "create")
        update_calls = sum(1 for case in test_cases if case["input"]["operation_requested"] == "update")
        delete_calls = sum(1 for case in test_cases if case["input"]["operation_requested"] == "delete")

        assert mock_forward_request_to_dynamo.call_count == create_calls + update_calls + delete_calls

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    @patch("forwarding_batch_lambda.forward_request_to_dynamo")
    @patch("forwarding_batch_lambda.create_table")
    @patch("forwarding_batch_lambda.make_batch_controller")
    def test_forward_lambda_handler_single_operations(
        self, mock_make_controller, mock_create_table, mock_forward_request_to_dynamo, mock_send_message
    ):
        """Test each operation independently in forward lambda handler.
        name: Description of the test case scenario,
        input: generates the kinesis row data for the event,
        expected_keys (list): expected output dictionary keys,
        expected_values (dict): expected output dictionary values
        dynamo_response: response for dynamo side effect
        All records are for the same file"""

        mock_create_table.return_value = {}
        mock_make_controller.return_value = mock_controller = MagicMock()

        test_cases = [
            {
                "name": "Single Create Success",
                "input": self.generate_input(row_id=1, operation_requested="create", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "imms_id"],
                "expected_values": {"row_id": "row-1", "imms_id": "IMMS1111"},
                "dynamo_response": "IMMS1111",
            },
            {
                "name": "Single Update Success",
                "input": self.generate_input(row_id=1, operation_requested="update", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "imms_id"],
                "expected_values": {"row_id": "row-1", "imms_id": "IMMS2222"},
                "dynamo_response": "IMMS2222",
            },
            {
                "name": "Single Delete Success",
                "input": self.generate_input(row_id=1, operation_requested="delete", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "imms_id"],
                "expected_values": {"row_id": "row-1", "imms_id": "IMMS3333"},
                "dynamo_response": "IMMS3333",
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                mock_send_message.reset_mock()

                mock_forward_request_to_dynamo.side_effect = lambda *args, **kwargs: test_case["dynamo_response"]

                event = self.generate_event([test_case])
                forward_lambda_handler(event, {})

                self.assert_forward_request_to_dynamo(mock_forward_request_to_dynamo, [test_case])
                self.assert_values_in_sqs_messages(mock_send_message, [test_case])

    @patch("forwarding_batch_lambda.sqs_client.send_message")
    @patch("forwarding_batch_lambda.forward_request_to_dynamo")
    @patch("forwarding_batch_lambda.create_table")
    @patch("forwarding_batch_lambda.make_batch_controller")
    def test_forward_lambda_handler_multiple_scenarios(
        self, mock_make_controller, mock_create_table, mock_forward_request_to_dynamo, mock_send_message
    ):
        """Test forward lambda handler with multiple rows in the event with create, update, and delete operations,
        and diagnostics handling.
            name: Description of the test case scenario,
            input: generates the kinesis row data for the event,
            expected_keys (list): expected output dictionary keys,
            expected_values (dict): expected output dictionary values
        Based on a maximum 10 rows received in event for the same file at a time to the forward_lambda_handler.
        All records are for the same file"""

        mock_create_table.return_value = {}
        mock_make_controller.return_value = mock_controller = MagicMock()
        mock_forward_request_to_dynamo.side_effect = [
            "IMMS123",
            IdentifierDuplicationError("Duplicate_Id"),
            "IMMS456",
            ResourceNotFoundError(resource_type="Immunization", resource_id=None),
            "IMMS789",
            Exception("Unexpected failure"),
            MessageNotSuccessfulError("Unable to reach API"),
            ResourceFoundError(resource_type="Immunization", resource_id="A-primary-key"),
            MessageNotSuccessfulError("Server error - FHIR JSON not correctly sent to forwarder"),
            CustomValidationError("An error from the record processor"),
        ]

        test_cases = [
            {
                "name": "Row 1: Create Success",
                "input": self.generate_input(row_id=1, operation_requested="create", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "imms_id"],
                "expected_values": {"row_id": "row-1", "imms_id": "IMMS123"},
            },
            {
                "name": "Row 2: Unexpected Error: Create failure ",
                "input": self.generate_input(row_id=2, operation_requested="create", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-2",
                    "diagnostics": create_diagnostics_dictionary(IdentifierDuplicationError("Duplicate_Id")),
                },
            },
            {
                "name": "Row 3: Update success",
                "input": self.generate_input(row_id=3, operation_requested="update", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "imms_id"],
                "expected_values": {"row_id": "row-3", "imms_id": "IMMS456"},
            },
            {
                "name": "Row 4: Update failure",
                "input": self.generate_input(row_id=4, operation_requested="update", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-4",
                    "diagnostics": create_diagnostics_dictionary(
                        ResourceNotFoundError(resource_type="Immunization", resource_id=None)
                    ),
                },
            },
            {
                "name": "Row 5: Delete Success",
                "input": self.generate_input(row_id=5, operation_requested="delete", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "imms_id"],
                "expected_values": {"row_id": "row-5", "imms_id": "IMMS789"},
            },
            {
                "name": "Row 6: Delete Failure",
                "input": self.generate_input(row_id=6, operation_requested="delete", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-6",
                    "diagnostics": create_diagnostics_dictionary(Exception("Unexpected failure")),
                },
            },
            {
                "name": "Row 7: Diagnostics Already Present",
                "input": self.generate_input(
                    row_id=7,
                    operation_requested="create",
                    include_fhir_json=True,
                ),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-7",
                    "diagnostics": create_diagnostics_dictionary(MessageNotSuccessfulError("Unable to reach API")),
                },
            },
            {
                "name": "Row 8: Delete Failure",
                "input": self.generate_input(row_id=8, operation_requested="delete", include_fhir_json=True),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-8",
                    "diagnostics": create_diagnostics_dictionary(
                        ResourceFoundError(resource_type="Immunization", resource_id="A-primary-key")
                    ),
                },
            },
            {
                "name": "Row 9: FHIR_JSON does not exist",
                "input": self.generate_input(row_id=9, operation_requested="create"),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-9",
                    "diagnostics": create_diagnostics_dictionary(
                        MessageNotSuccessfulError("Server error - FHIR JSON not correctly sent to forwarder")
                    ),
                },
            },
            {
                "name": "Row 10: Validation error exists from record processor",
                "input": self.generate_input(row_id=10, operation_requested="update"),
                "expected_keys": ["file_key", "row_id", "created_at_formatted_string", "local_id", "diagnostics"],
                "expected_values": {
                    "row_id": "row-10",
                    "diagnostics": create_diagnostics_dictionary(
                        CustomValidationError("An error from the record processor")
                    ),
                },
            },
        ]

        event = self.generate_event(test_cases)

        forward_lambda_handler(event, {})

        self.assert_forward_request_to_dynamo(mock_forward_request_to_dynamo, test_cases)
        self.total_forward_request_to_dynamo(mock_forward_request_to_dynamo, test_cases)

        self.assert_values_in_sqs_messages(mock_send_message, test_cases)

    def test_create_diagnostics_dictionary(self):

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


if __name__ == "__main__":
    unittest.main()
