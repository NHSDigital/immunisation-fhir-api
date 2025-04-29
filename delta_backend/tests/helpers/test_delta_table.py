# import json
# import unittest
# import os
# import time
# from datetime import datetime, timedelta
# from decimal import Decimal
# from copy import deepcopy
# from unittest import TestCase
# from unittest.mock import patch, Mock
# from moto import mock_dynamodb, mock_sqs
# from boto3 import resource as boto3_resource, client as boto3_client
# from tests.utils_for_converter_tests import ValuesForTests, ErrorValuesForTests
# from botocore.config import Config
# from pathlib import Path
# from zoneinfo import ZoneInfo
# from SchemaParser import SchemaParser
# from Converter import Converter
# from ConversionChecker import ConversionChecker, RecordError
# import ExceptionMessages

# MOCK_ENV_VARS = {
#     "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
#     "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
#     "SOURCE": "test-source",
# }
# request_json_data = ValuesForTests.json_data
# with patch.dict("os.environ", MOCK_ENV_VARS):
#     from delta import handler, Converter

# class TestRecordError(unittest.TestCase):
#     def test_fields_and_str(self):
#         err = RecordError(
#             code=5,
#             message="Test failed",
#             details="Something went wrong"
#         )

#         # The attributes should round‑trip
#         self.assertEqual(err.code, 5)
#         self.assertEqual(err.message, "Test failed")
#         self.assertEqual(err.details, "Something went wrong")

#         # __repr__ and __str__ both produce the tuple repr
#         expected = "(5, 'Test failed', 'Something went wrong')"
#         self.assertEqual(str(err),   expected)
#         self.assertEqual(repr(err),  expected)

#     def test_default_args(self):
#         # If you omit arguments they default to None
#         err = RecordError()
#         self.assertIsNone(err.code)
#         self.assertIsNone(err.message)
#         self.assertIsNone(err.details)

#         # repr shows three Nones
#         self.assertEqual(str(err), "(None, None, None)")

# @patch.dict("os.environ", MOCK_ENV_VARS, clear=True)
# @mock_dynamodb
# @mock_sqs
# class TestConvertToFlatJson(unittest.TestCase):
#     maxDiff = None
#     def setUp(self):
#         """Set up mock DynamoDB table."""
#         self.dynamodb_resource = boto3_resource("dynamodb", "eu-west-2")
#         self.table = self.dynamodb_resource.create_table(
#             TableName="immunisation-batch-internal-dev-audit-test-table",
#             KeySchema=[
#                 {"AttributeName": "PK", "KeyType": "HASH"},
#             ],
#             AttributeDefinitions=[
#                 {"AttributeName": "PK", "AttributeType": "S"},
#                 {"AttributeName": "Operation", "AttributeType": "S"},
#                 {"AttributeName": "IdentifierPK", "AttributeType": "S"},
#                 {"AttributeName": "SupplierSystem", "AttributeType": "S"},
#             ],
#             ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
#             GlobalSecondaryIndexes=[
#                 {
#                     "IndexName": "IdentifierGSI",
#                     "KeySchema": [{"AttributeName": "IdentifierPK", "KeyType": "HASH"}],
#                     "Projection": {"ProjectionType": "ALL"},
#                     "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
#                 },
#                 {
#                     "IndexName": "PatientGSI",
#                     "KeySchema": [
#                         {"AttributeName": "Operation", "KeyType": "HASH"},
#                         {"AttributeName": "SupplierSystem", "KeyType": "RANGE"},
#                     ],
#                     "Projection": {"ProjectionType": "ALL"},
#                     "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
#                 },
#             ],
#         )
#         self.logger_info_patcher = patch("logging.Logger.info")
#         self.mock_logger_info = self.logger_info_patcher.start()

#         self.logger_exception_patcher = patch("logging.Logger.exception")
#         self.mock_logger_exception = self.logger_exception_patcher.start()

#         self.firehose_logger_patcher = patch("delta.firehose_logger")
#         self.mock_firehose_logger = self.firehose_logger_patcher.start()

#         self.write_to_db_patcher = patch("helpers.delta_data.DeltaData.write_to_db")
#         self.mock_write_to_db = self.write_to_db_patcher.start()
#         self.mock_write_to_db.return_value = (
#             {"ResponseMetadata": {"HTTPStatusCode": 200}},  # Mock response
#             []  # Mock error records
#         )

#     def tearDown(self):
#         self.logger_exception_patcher.stop()
#         self.logger_info_patcher.stop()
#         self.mock_firehose_logger.stop()
#         self.write_to_db_patcher.stop()

#     @staticmethod
#     def get_event(event_name="INSERT", operation="operation", supplier="EMIS"):
#         """Returns test event data."""
#         return ValuesForTests.get_event(event_name, operation, supplier)

#     def test_handler_imms_convert_to_flat_json(self):
#         """Test that the Imms field contains the correct flat JSON data for CREATE, UPDATE, and DELETE operations."""
#         expected_action_flags = [
#             {"Operation": "CREATE", "EXPECTED_ACTION_FLAG": "NEW"},
#             {"Operation": "UPDATE", "EXPECTED_ACTION_FLAG": "UPDATE"},
#             {"Operation": "DELETE", "EXPECTED_ACTION_FLAG": "DELETE"},
#         ]

#         for test_case in expected_action_flags:
#             with self.subTest(test_case["Operation"]):

#                 event = self.get_event(operation=test_case["Operation"])

#                 response = handler(event, None)

#                 # Retrieve items from DynamoDB
#                 result = self.table.scan()
#                 items = result.get("Items", [])

#                 expected_values = ValuesForTests.expected_static_values
#                 expected_imms = ValuesForTests.get_expected_imms(test_case["EXPECTED_ACTION_FLAG"])

#                 self.assert_dynamodb_record(
#                     test_case["EXPECTED_ACTION_FLAG"], items, expected_values, expected_imms, response
#                 )

#                 result = self.table.scan()
#                 items = result.get("Items", [])
#                 self.clear_table()


#     if __name__ == "__main__":
#         unittest.main()