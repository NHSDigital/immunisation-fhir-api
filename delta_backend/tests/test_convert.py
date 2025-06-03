# import json
# import unittest
# from copy import deepcopy
# from unittest.mock import patch, Mock
# from moto import mock_aws
# from boto3 import resource as boto3_resource
# from utils_for_converter_tests import ValuesForTests, ErrorValuesForTests
# from converter import Converter
# from common.mappings import ActionFlag, Operation, EventName

# MOCK_ENV_VARS = {
#     "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
#     "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
#     "SOURCE": "test-source",
# }
# request_json_data = ValuesForTests.json_data
# with patch.dict("os.environ", MOCK_ENV_VARS):
#     from delta import handler, Converter


# @patch.dict("os.environ", MOCK_ENV_VARS, clear=True)
# class TestConvertToFlatJson(unittest.TestCase):
#     maxDiff = None
#     def setUp(self):
#         # Start moto AWS mocks
#         self.mock = mock_aws()
#         self.mock.start()
    
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

#     def tearDown(self):
#         self.logger_exception_patcher.stop()
#         self.logger_info_patcher.stop()
#         self.mock_firehose_logger.stop()
        
#         self.mock.stop()

#     @staticmethod
#     def get_event(event_name=EventName.CREATE, operation="operation", supplier="EMIS"):
#         """Returns test event data."""
#         return ValuesForTests.get_event(event_name, operation, supplier)

#     def assert_dynamodb_record(self, operation_flag, action_flag, items, expected_values, expected_imms, response):
#         """
#         Asserts that a record with the expected structure exists in DynamoDB.
#         Ignores dynamically generated fields like PK, DateTimeStamp, and ExpiresAt.
#         Ensures that the 'Imms' field matches exactly.
#         """
#         self.assertTrue(response)

#         filtered_items = [
#             {k: v for k, v in item.items() if k not in ["PK", "DateTimeStamp", "ExpiresAt"]}
#             for item in items
#             if item.get("Operation") == operation_flag
#             and item.get("Imms", {}).get("ACTION_FLAG") == action_flag
#         ]

#         self.assertGreater(len(filtered_items), 0, f"No matching item found for {operation_flag}")

#         imms_data = filtered_items[0]["Imms"]
#         self.assertIsInstance(imms_data, dict)
#         self.assertGreater(len(imms_data), 0)

#         # Check Imms JSON structure matches exactly
#         self.assertEqual(imms_data, expected_imms, "Imms data does not match expected JSON structure")

#         for key, expected_value in expected_values.items():
#             self.assertIn(key, filtered_items[0], f"{key} is missing")
#             self.assertEqual(filtered_items[0][key], expected_value, f"{key} mismatch")

#     def test_fhir_converter_json_direct_data(self):
#         """it should convert fhir json data to flat json"""
#         json_data = json.dumps(ValuesForTests.json_data)

#         fhir_converter = Converter(json_data)
#         FlatFile = fhir_converter.run_conversion()

#         flatJSON = json.dumps(FlatFile)
#         expected_imms_value = deepcopy(ValuesForTests.expected_imms2)  # UPDATE is currently the default action-flag
#         expected_imms = json.dumps(expected_imms_value)
#         self.assertEqual(flatJSON, expected_imms)

#         errorRecords = fhir_converter.get_error_records()

#         self.assertEqual(len(errorRecords), 0)
        
#     def test_fhir_converter_json_direct_data(self):
#         """it should convert fhir json data to flat json"""
#         json_data = json.dumps(ValuesForTests.json_data)

#         fhir_converter = Converter(json_data)
#         FlatFile = fhir_converter.run_conversion()

#         flatJSON = json.dumps(FlatFile)
#         expected_imms_value = deepcopy(ValuesForTests.expected_imms2)  # UPDATE is currently the default action-flag
#         expected_imms = json.dumps(expected_imms_value)
#         self.assertEqual(flatJSON, expected_imms)

#         errorRecords = fhir_converter.get_error_records()

#         self.assertEqual(len(errorRecords), 0)

#     def test_fhir_converter_json_error_scenario_reporting_on(self):
#         """it should convert fhir json data to flat json - error scenarios"""
#         error_test_cases = [ErrorValuesForTests.missing_json, ErrorValuesForTests.json_dob_error]

#         for test_case in error_test_cases:
#             json_data = json.dumps(test_case)

#             fhir_converter = Converter(json_data)
#             fhir_converter.run_conversion()

#             errorRecords = fhir_converter.get_error_records()

#             # Check if bad data creates error records
#             self.assertTrue(len(errorRecords) > 0)
            
#     def test_fhir_converter_json_error_scenario_reporting_off(self):
#         """it should convert fhir json data to flat json - error scenarios"""
#         error_test_cases = [ErrorValuesForTests.missing_json, ErrorValuesForTests.json_dob_error]

#         for test_case in error_test_cases:
#             json_data = json.dumps(test_case)

#             fhir_converter = Converter(json_data, report_unexpected_exception=False)
#             fhir_converter.run_conversion()

#             errorRecords = fhir_converter.get_error_records()

#             # Check if bad data creates error records
#             self.assertTrue(len(errorRecords) == 0)
            
#     def test_fhir_converter_json_incorrect_data_scenario_reporting_on(self):
#         """it should convert fhir json data to flat json - error scenarios"""

#         with self.assertRaises(ValueError):
#             fhir_converter = Converter(None)
#             errorRecords = fhir_converter.get_error_records()
#             self.assertTrue(len(errorRecords) > 0)
    
    
#     def test_fhir_converter_json_incorrect_data_scenario_reporting_off(self):
#         """it should convert fhir json data to flat json - error scenarios"""

#         with self.assertRaises(ValueError):
#             fhir_converter = Converter(None, report_unexpected_exception=False)
#             errorRecords = fhir_converter.get_error_records()
#             self.assertTrue(len(errorRecords) == 0)

#     def test_handler_imms_convert_to_flat_json(self):
#         """Test that the Imms field contains the correct flat JSON data for CREATE, UPDATE, and DELETE operations."""
#         expected_action_flags = [
#             {"Operation": Operation.CREATE, "EXPECTED_ACTION_FLAG": ActionFlag.CREATE},
#             {"Operation": Operation.UPDATE, "EXPECTED_ACTION_FLAG": ActionFlag.UPDATE},
#             {"Operation": Operation.DELETE_LOGICAL, "EXPECTED_ACTION_FLAG": ActionFlag.DELETE_LOGICAL},
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
#                     test_case["Operation"],
#                     test_case["EXPECTED_ACTION_FLAG"],
#                     items,
#                     expected_values,
#                     expected_imms,
#                     response
#                 )

#                 result = self.table.scan()
#                 items = result.get("Items", [])
#                 self.clear_table()

#     def clear_table(self):
#         scan = self.table.scan()
#         with self.table.batch_writer() as batch:
#             for item in scan.get("Items", []):
#                 batch.delete_item(Key={"PK": item["PK"]})
#         result = self.table.scan()
#         items = result.get("Items", [])

#     if __name__ == "__main__":
#         unittest.main()
