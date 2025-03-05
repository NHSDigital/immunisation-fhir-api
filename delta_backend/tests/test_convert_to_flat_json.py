import json
import unittest
import os
import time
from decimal import Decimal
from copy import deepcopy
from unittest import TestCase
from moto import mock_dynamodb, mock_sqs
from boto3 import resource as boto3_resource, client as boto3_client
from tests.utils_for_converter_tests import ValuesForTests, ErrorValuesForTests
from unittest.mock import patch
from botocore.config import Config
from pathlib import Path


MOCK_ENV_VARS = {
    "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
    "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
    "SOURCE": "test-source",
}

with patch.dict("os.environ", MOCK_ENV_VARS):
    from delta import handler, Converter
    from Converter import imms, ErrorRecords


@patch.dict("os.environ", MOCK_ENV_VARS, clear=True)
@mock_dynamodb
@mock_sqs
class TestConvertToFlatJson(unittest.TestCase):

    def setUp(self):
        """Set up mock DynamoDB table."""
        self.dynamodb_resource = boto3_resource("dynamodb", "eu-west-2")
        self.table = self.dynamodb_resource.create_table(
            TableName="immunisation-batch-internal-dev-audit-test-table",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "Operation", "AttributeType": "S"},
                {"AttributeName": "IdentifierPK", "AttributeType": "S"},
                {"AttributeName": "SupplierSystem", "AttributeType": "S"},
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
                        {"AttributeName": "Operation", "KeyType": "HASH"},
                        {"AttributeName": "SupplierSystem", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
            ],
        )

    @staticmethod
    def get_event(event_name="INSERT", operation="operation", supplier="EMIS"):
        """Returns test event data."""
        return ValuesForTests.get_event(event_name, operation, supplier)

    def assert_dynamodb_record(self, operation_flag, items, expected_values, expected_imms, response):
        """
        Asserts that a record with the expected structure exists in DynamoDB.
        Ignores dynamically generated fields like PK, DateTimeStamp, and ExpiresAt.
        Ensures that the 'Imms' field matches exactly.
        """
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], "Records processed successfully")

        filtered_items = [
            {k: v for k, v in item.items() if k not in ["PK", "DateTimeStamp", "ExpiresAt"]}
            for item in items
            if item.get("Operation") == operation_flag
        ]

        self.assertGreater(len(filtered_items), 0, f"No matching item found for {operation_flag}")

        imms_data = filtered_items[0]["Imms"]
        self.assertIsInstance(imms_data, list)
        self.assertGreater(len(imms_data), 0)

        # Check Imms JSON structure matches exactly
        self.assertEqual(imms_data, expected_imms, "Imms data does not match expected JSON structure")

        for key, expected_value in expected_values.items():
            self.assertIn(key, filtered_items[0], f"{key} is missing")
            self.assertEqual(filtered_items[0][key], expected_value, f"{key} mismatch")

    def test_fhir_converter_json_direct_data(self):
        """it should convert json data to flat fhir"""
        imms.clear()
        json_data = json.dumps(ValuesForTests.json_data)

        start = time.time()

        FHIRConverter = Converter(json_data)
        FlatFile = FHIRConverter.runConversion(False, True)

        flatJSON = json.dumps(FlatFile)

        expected_imms_value = deepcopy(ValuesForTests.expected_imms)  # UPDATE is currently the default action-flag
        expected_imms = json.dumps(expected_imms_value)
        self.assertEqual(flatJSON, expected_imms)

        errorRecords = FHIRConverter.getErrorRecords()

        if len(errorRecords) > 0:
            print("Converted With Errors")
        else:
            print("Converted Successfully")

        end = time.time()
        print(end - start)

    def test_fhir_converter_json_error_scenario(self):
        """it should convert json data to flat fhir - error scenarios"""
        error_test_cases = [ErrorValuesForTests.missing_json, ErrorValuesForTests.json_dob_error]

        for test_case in error_test_cases:
            imms.clear()
            ErrorRecords.clear()
            json_data = json.dumps(test_case)

            start = time.time()

            FHIRConverter = Converter(json_data)
            FlatFile = FHIRConverter.runConversion(False, True)

            flatJSON = json.dumps(FlatFile)

            # if len(flatJSON) > 0:
            #     print(flatJSON)
            # Fix error handling
            # expected_imms = ErrorValuesForTests.get_expected_imms_error_output
            # self.assertEqual(flatJSON, expected_imms)

            errorRecords = FHIRConverter.getErrorRecords()

            if len(errorRecords) > 0:
                print("Converted With Errors")
                print(f"Error records -error scenario {errorRecords}")
            else:
                print("Converted Successfully")

            end = time.time()
            print(end - start)

    def test_handler_imms_convert_to_flat_json(self):
        """Test that the Imms field contains the correct flat JSON data for CREATE, UPDATE, and DELETE operations."""
        expected_action_flags = [
            {"Operation": "CREATE", "EXPECTED_ACTION_FLAG": "NEW"},
            {"Operation": "UPDATE", "EXPECTED_ACTION_FLAG": "UPDATE"},
            {"Operation": "DELETE", "EXPECTED_ACTION_FLAG": "DELETE"},
        ]

        for test_case in expected_action_flags:
            with self.subTest(test_case["Operation"]):
                imms.clear()

                event = self.get_event(operation=test_case["Operation"])

                response = handler(event, None)

                # Retrieve items from DynamoDB
                result = self.table.scan()
                items = result.get("Items", [])

                expected_values = ValuesForTests.expected_static_values
                expected_imms = ValuesForTests.get_expected_imms(test_case["EXPECTED_ACTION_FLAG"])

                self.assert_dynamodb_record(
                    test_case["EXPECTED_ACTION_FLAG"], items, expected_values, expected_imms, response
                )

                result = self.table.scan()
                items = result.get("Items", [])
                self.clear_table()

    def clear_table(self):
        scan = self.table.scan()
        with self.table.batch_writer() as batch:
            for item in scan.get("Items", []):
                batch.delete_item(Key={"PK": item["PK"]})
        result = self.table.scan()
        items = result.get("Items", [])

    if __name__ == "__main__":
        unittest.main()
