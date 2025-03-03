import json
import unittest
import os
from unittest import TestCase
from moto import mock_dynamodb, mock_sqs
from boto3 import resource as boto3_resource, client as boto3_client
from tests.Utils_converter import ValuesForTests
from unittest.mock import patch
from botocore.config import Config

MOCK_ENV_VARS = {
    "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
    "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
    "SOURCE": "test-source",
}

patch.dict(os.environ, MOCK_ENV_VARS).start()
from delta import handler


@mock_dynamodb
@mock_sqs
class TestHandler(TestCase):

    def setUp(self):
        """Set up mock DynamoDB table."""
        self.mock_dynamodb = mock_dynamodb()
        self.mock_dynamodb.start()
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
                        {"AttributeName": "SupplierSystem", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
            ],
        )

    @classmethod
    def tearDownClass(cls):
        dynamodb_resource = boto3_resource("dynamodb", "eu-west-2")
        table = dynamodb_resource.Table("immunisation-batch-internal-dev-audit-test-table")
        table.delete()
        table.wait_until_not_exists()

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

    def test_handler_imms_flat_json(self):
        """Test that the Imms field contains the correct flat JSON data for CREATE, UPDATE, and DELETE operations."""
        expected_action_flags = {"CREATE": "NEW", "UPDATE": "UPDATE", "DELETE": "DELETE"}

        for operation, expected_action_flag in expected_action_flags.items():
            with self.subTest(operation=operation):

                event = self.get_event(operation=operation)

                # Call the handler
                response = handler(event, None)

                # Verify response success
                # self.assertEqual(response["statusCode"], 200)
                # self.assertEqual(response["body"], "Records processed successfully")

                # Retrieve items from DynamoDB
                result = self.table.scan()
                items = result.get("Items", [])
                # print(f"DYNAMO THESE ITEMS : {items}")

                # Fetch expected values from the module
                expected_values = ValuesForTests.expected_static_values
                expected_imms = ValuesForTests.get_expected_imms(expected_action_flag)
                # print(f"EXPETECED IMMS : {expected_imms}")
                # Call the assertion function
                self.assert_dynamodb_record(expected_action_flag, items, expected_values, expected_imms, response)
                self.tearDown()
                # self.tearDown()
                result = self.table.scan()
                items = result.get("Items", [])
                # print(f"AFTER tests runDYNAMO THESE ITEMS : {items}")

        def tearDown(self):
            scan = self.table.scan()
            with self.table.batch_writer() as batch:
                for item in scan.get("Items", []):
                    batch.delete_item(Key={"PK": item["PK"]})
            result = self.table.scan()
            items = result.get("Items", [])
            # print(f"FINAL TABLE ITEMS DYNAMO: {items}")

        # result = self.table.scan()
        # items = result.get("Items", [])
        # print(f"FINAL TABLE ITEMS DYNAMO: {items}")

    if __name__ == "__main__":
        unittest.main()
