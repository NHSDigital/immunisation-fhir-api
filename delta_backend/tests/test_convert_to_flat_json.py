import json
import unittest
from copy import deepcopy
from unittest.mock import patch, Mock
from moto import mock_dynamodb, mock_sqs
from boto3 import resource as boto3_resource
from utils_for_converter_tests import ValuesForTests, ErrorValuesForTests
from schema_parser import SchemaParser
from delta_converter import Converter
from conversion_checker import ConversionChecker
from common.mappings import ActionFlag, Operation, EventName
import exception_messages

MOCK_ENV_VARS = {
    "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
    "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
    "SOURCE": "test-source",
}
request_json_data = ValuesForTests.json_data
with patch.dict("os.environ", MOCK_ENV_VARS):
    from delta import handler, Converter


@patch.dict("os.environ", MOCK_ENV_VARS, clear=True)
@mock_dynamodb
@mock_sqs
class TestConvertToFlatJson(unittest.TestCase):
    maxDiff = None
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
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.firehose_logger_patcher = patch("delta.firehose_logger")
        self.mock_firehose_logger = self.firehose_logger_patcher.start()

    def tearDown(self):
        self.logger_exception_patcher.stop()
        self.logger_info_patcher.stop()
        self.mock_firehose_logger.stop()

    @staticmethod
    def get_event(event_name=EventName.CREATE, operation="operation", supplier="EMIS"):
        """Returns test event data."""
        return ValuesForTests.get_event(event_name, operation, supplier)

    def assert_dynamodb_record(self, operation_flag, action_flag, items, expected_values, expected_imms, response):
        """
        Asserts that a record with the expected structure exists in DynamoDB.
        Ignores dynamically generated fields like PK, DateTimeStamp, and ExpiresAt.
        Ensures that the 'Imms' field matches exactly.
        """
        self.assertTrue(response)

        filtered_items = [
            {k: v for k, v in item.items() if k not in ["PK", "DateTimeStamp", "ExpiresAt"]}
            for item in items
            if item.get("Operation") == operation_flag
            and item.get("Imms", {}).get("ACTION_FLAG") == action_flag
        ]

        self.assertGreater(len(filtered_items), 0, f"No matching item found for {operation_flag}")

        imms_data = filtered_items[0]["Imms"]
        self.assertIsInstance(imms_data, dict)
        self.assertGreater(len(imms_data), 0)

        # Check Imms JSON structure matches exactly
        self.assertEqual(imms_data, expected_imms, "Imms data does not match expected JSON structure")

        for key, expected_value in expected_values.items():
            self.assertIn(key, filtered_items[0], f"{key} is missing")
            self.assertEqual(filtered_items[0][key], expected_value, f"{key} mismatch")

    def test_fhir_converter_json_direct_data(self):
        """it should convert fhir json data to flat json"""
        json_data = json.dumps(ValuesForTests.json_data)

        FHIRConverter = Converter(json_data)
        FlatFile = FHIRConverter.run_conversion()

        flatJSON = json.dumps(FlatFile)
        expected_imms_value = deepcopy(ValuesForTests.expected_imms2)  # UPDATE is currently the default action-flag
        expected_imms = json.dumps(expected_imms_value)
        self.assertEqual(flatJSON, expected_imms)

        errorRecords = FHIRConverter.get_error_records()

        self.assertEqual(len(errorRecords), 0)

    def test_fhir_converter_json_error_scenario(self):
        """it should convert fhir json data to flat json - error scenarios"""
        error_test_cases = [ErrorValuesForTests.missing_json, ErrorValuesForTests.json_dob_error]

        for test_case in error_test_cases:
            json_data = json.dumps(test_case)

            FHIRConverter = Converter(json_data)
            FHIRConverter.run_conversion()

            errorRecords = FHIRConverter.get_error_records()

            # Check if bad data creates error records
            self.assertTrue(len(errorRecords) > 0)

    def test_handler_imms_convert_to_flat_json(self):
        """Test that the Imms field contains the correct flat JSON data for CREATE, UPDATE, and DELETE operations."""
        expected_action_flags = [
            {"Operation": Operation.CREATE, "EXPECTED_ACTION_FLAG": ActionFlag.CREATE},
            {"Operation": Operation.UPDATE, "EXPECTED_ACTION_FLAG": ActionFlag.UPDATE},
            {"Operation": Operation.DELETE_LOGICAL, "EXPECTED_ACTION_FLAG": ActionFlag.DELETE_LOGICAL},
        ]

        for test_case in expected_action_flags:
            with self.subTest(test_case["Operation"]):

                event = self.get_event(operation=test_case["Operation"])

                response = handler(event, None)

                # Retrieve items from DynamoDB
                result = self.table.scan()
                items = result.get("Items", [])

                expected_values = ValuesForTests.expected_static_values
                expected_imms = ValuesForTests.get_expected_imms(test_case["EXPECTED_ACTION_FLAG"])

                self.assert_dynamodb_record(
                    test_case["Operation"],
                    test_case["EXPECTED_ACTION_FLAG"],
                    items,
                    expected_values,
                    expected_imms,
                    response
                )

                result = self.table.scan()
                items = result.get("Items", [])
                self.clear_table()

    # TODO revisit and amend if necessary
    @patch("delta_converter.FHIRParser")
    @patch("delta_converter.ConversionLayout")
    def test_fhir_parser_exception(self, mock_fhir_parser):
        # Mock FHIRParser to raise an exception
        mock_fhir_parser.side_effect = Exception("FHIR Parsing Error")
        converter = Converter(fhir_data="some_data")

        # Check if the error message was added to ErrorRecords
        errors = converter.get_error_records()
        self.assertEqual(len(errors), 1)
        self.assertIn("Initialization failed: [JSONDecodeError]", errors[0]["message"])
        self.assertEqual(errors[0]["code"], 0)

    @patch("delta_converter.FHIRParser")
    @patch("delta_converter.SchemaParser")
    def test_schema_parser_exception(self, mock_schema_parser, mock_fhir_parser):

        # Mock FHIRParser to return normally
        mock_fhir_instance = Mock()
        mock_fhir_instance.parseFHIRData.return_value = None
        mock_fhir_parser.return_value = mock_fhir_instance

        # Mock SchemaParser to raise an exception
        mock_schema_parser.side_effect = Exception("Schema Parsing Error")
        converter = Converter(fhir_data="{}")

        # Check if the error message was added to ErrorRecords
        errors = converter.get_error_records()
        self.assertEqual(len(errors), 1)
        self.assertIn("Schema Parser Unexpected exception", errors[0]["message"])
        self.assertEqual(errors[0]["code"], 0)

    @patch("delta_converter.ConversionChecker")
    def test_conversion_checker_exception(self, mock_conversion_checker):
        # Mock ConversionChecker to raise an exception
        mock_conversion_checker.side_effect = Exception("Conversion Checking Error")
        converter = Converter(fhir_data="some_data")

        # Check if the error message was added to ErrorRecords
        self.assertEqual(len(converter.get_error_records()), 1)
        self.assertIn(
            "Initialization failed: [JSONDecodeError]",
            converter.get_error_records()[0]["message"],
        )
        self.assertEqual(converter.get_error_records()[0]["code"], 0)

    @patch("delta_converter.SchemaParser.get_conversions")
    def test_get_conversions_exception(self, mock_get_conversions):
        # Mock get_conversions to raise an exception
        mock_get_conversions.side_effect = Exception("Error while getting conversions")
        converter = Converter(fhir_data="some_data")

        # Check if the error message was added to ErrorRecords
        self.assertEqual(len(converter.get_error_records()), 1)
        self.assertIn(
            "Initialization failed: [JSONDecodeError]",
            converter.get_error_records()[0]["message"],
        )
        self.assertEqual(converter.get_error_records()[0]["code"], 0)

    @patch("delta_converter.SchemaParser.get_conversions")
    @patch("delta_converter.FHIRParser.get_key_value")
    def test_conversion_exceptions(self, mock_get_key_value, mock_get_conversions):
        mock_get_conversions.side_effect = Exception("Error while getting conversions")
        mock_get_key_value.side_effect = Exception("Key value retrieval failed")
        converter = Converter(fhir_data="some_data")

        schema = {
            "conversions": [
                {
                    "fieldNameFHIR": "some_field",
                    "fieldNameFlat": "flat_field",
                    "expression": {"expressionType": "type", "expressionRule": "rule"},
                }
            ]
        }
        converter.SchemaFile = schema
        error_records = converter.get_error_records()
        self.assertEqual(len(error_records), 1)

        self.assertIn(
            "Initialization failed: [JSONDecodeError]",
            error_records[0]["message"],
        )
        self.assertEqual(error_records[0]["code"], 0)

    def test_log_error(self):
        # Instantiate ConversionChecker
        checker = ConversionChecker(dataParser=None, summarise=False, report_unexpected_exception=True)

        # Simulate an exception
        exception = ValueError("Invalid value")

        # Call the _log_error method twice to also check deduplication
        checker._log_error("test_field", "test_value", exception)
        checker._log_error("test_field", "test_value", exception)

        # Assert that only one error record is added due to deduplication
        self.assertEqual(len(checker.errorRecords), 2)

        # Assert that one error record is added
        self.assertEqual(len(checker.errorRecords), 2)
        error = checker.errorRecords[0]

        # Assert that the error record contains correct details
        self.assertEqual(error["field"], "test_field")
        self.assertEqual(error["value"], "test_value")
        self.assertIn("Invalid value", error["message"])
        self.assertEqual(error["code"], exception_messages.RECORD_CHECK_FAILED)

    def test_convert_to_not_empty(self):

        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        result = checker._convertToNotEmpty(None, "fieldName", "Some data", False, True)
        self.assertEqual(result, "Some data")

        result = checker._convertToNotEmpty(None, "fieldName", "", False, True)
        self.assertEqual(result, "")

        # Test for value that is not a string
        checker._log_error = Mock()
        result = checker._convertToNotEmpty(None, "fieldName", 12345, False, True)
        self.assertEqual(result, "")

        checker._log_error.assert_called_once()

        field, value, err = checker._log_error.call_args[0]
        self.assertEqual((field, value), ("fieldName",12345))
        self.assertIsInstance(err, str)
        self.assertIn("Value not a String", err)

        checker._log_error.reset_mock()

        # Simulate a fieldValue whose .strip() crashes to test exception handling
        checker._log_error = Mock()

        class BadString(str):
            def strip(self):
                raise RuntimeError("Simulated crash during strip")

        bad_value = BadString("some bad string")

        # Make the .strip() method crash
        result = checker._convertToNotEmpty(None, "fieldName", bad_value, False, True)
        self.assertEqual(result, "")  # Should return empty string on exception
        checker._log_error.assert_called_once()
        field, value, message = checker._log_error.call_args[0]
        self.assertEqual((field, value), ("fieldName", bad_value))
        self.assertIsInstance(message, str)
        self.assertIn("RuntimeError", message)

    def test_convert_to_nhs_number(self):

        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

         # Test empty NHS number
        empty_nhs_number = ""
        result = checker._convertToNHSNumber(None, "fieldName", empty_nhs_number, False, True)
        self.assertEqual(result, "", "Expected empty string for empty NHS number input")

        # Test valid NHS number
        valid_nhs_number = "6000000000"
        result = checker._convertToNHSNumber("NHSNUMBER", "fieldName", valid_nhs_number, False, True)
        self.assertEqual(result, "6000000000", "Valid NHS number should be returned as-is")

        # Test invalid NHS number
        invalid_nhs_number = "1234567890243"
        result = checker._convertToNHSNumber("NHSNUMBER","fieldName", invalid_nhs_number, False, True)
        self.assertEqual(result, "", "Invalid NHS number should return empty string")

    def test_convert_to_date(self):
        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

         # 1. Valid full date
        result = checker._convertToDate("%Y%m%d", "fieldName", "2022-01-01", False, True)
        self.assertEqual(result, "20220101")

        # 2.Full ISO date should be transformed to YYYYMMDD
        result = checker._convertToDate("%Y%m%d", "fieldName", "2022-01-01T12:00:00+00:00", False, True)
        self.assertEqual(result, "20220101")

        # 3. Invalid string date format (should trigger "Date must be in YYYYMMDD format")
        result = checker._convertToDate("%Y%m%d", "fieldName", "invalid_date", False, True)
        self.assertEqual(result, "")

        # 4. None input (should return empty without logging)
        result = checker._convertToDate("%Y%m%d", "fieldName", None, False, True)
        self.assertEqual(result, "")

        # 5. Not a string input (should trigger "Value is not a string")
        result = checker._convertToDate("%Y%m%d", "fieldName", 12345678, False, True)
        self.assertEqual(result, "")

        # 6 Empty string
        result = checker._convertToDate("%Y%m%d", "fieldName", "", False, True)
        self.assertEqual(result, "")

        # 7 Validate all error logs of various responses
        messages = [err["message"] for err in checker.errorRecords]

        self.assertIn("Value is not a string", messages)

        # Confirm Total Errors Per conversion
        self.assertEqual(len(checker.errorRecords), 2)

        # Test for value Error
        checker._log_error = Mock()

        # invalid date against the given format → ValueError path
        result = checker._convertToDate("format:%Y-%m-%d", "fieldName", "not-a-date", False, True)
        self.assertEqual(result, "")

        # ensure we logged exactly that ValueError
        checker._log_error.assert_called_once()
        field, value, err = checker._log_error.call_args[0]
        self.assertEqual((field, value), ("fieldName", "not-a-date"))
        self.assertIsInstance(err, ValueError)

    def test_convert_to_date_time(self):
        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        valid_date_time = "2025-01-01T12:00:00+00:00"
        result = checker._convertToDateTime("fhir-date", "fieldName", valid_date_time, False, True)
        self.assertEqual(result, "20250101T12000000")

        valid_fhir_date = "2025-01-01T13:28:17+00:00"
        result = checker._convertToDateTime("fhir-date", "fieldName", valid_fhir_date, False, True)
        self.assertEqual(result, "20250101T13281700")

        valid_fhir_date = "2022-01-01"
        result = checker._convertToDateTime("", "fieldName", valid_fhir_date, False, True)
        self.assertEqual(result, "20220101T00000000")

        valid_fhir_date = "2025-05-01T13:28:17+01:00"
        result = checker._convertToDateTime("fhir-date", "fieldName", valid_fhir_date, False, True)
        self.assertEqual(result, "20250501T13281701")

        invalid_date_time = "invalid_date_time"
        result = checker._convertToDateTime("fhir-date", "fieldName", invalid_date_time, False, True)
        self.assertEqual(result, "")

        valid_date_time = "2025-01-01T12:00:00+03:00"
        result = checker._convertToDateTime("fhir-date", "fieldName", valid_date_time, False, True)
        self.assertEqual(result, "")

        messages = [err["message"] for err in checker.errorRecords]

        self.assertIn("Unexpected exception [ValueError]", messages[0])
        self.assertIn("Unsupported Format or offset", messages[1])

        # Confirm Total Errors Per conversion
        self.assertEqual(len(checker.errorRecords), 2)
        
        # Test for value Error
        checker._log_error = Mock()

        valid_fhir_date = "2022-01"
        result = checker._convertToDateTime("fhir-date", "fieldName", valid_fhir_date, False, True)
        self.assertEqual(result, "")

        # ensure we logged exactly that ValueError
        checker._log_error.assert_called_once()
        field, value, err = checker._log_error.call_args[0]
        self.assertEqual((field, value), ("fieldName", valid_fhir_date))
        self.assertIsInstance(err, ValueError)

    def test_convert_to_boolean(self):
        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        # Arrange
        dataParser = Mock()
        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        # 1. Boolean True passes through
        result = checker._convertToBoolean(None, "fieldName", True, False, True)
        self.assertTrue(result)

        # 2. Boolean False passes through
        result = checker._convertToBoolean(None, "fieldName", False, False, True)
        self.assertFalse(result)

        # 3. String "true" variants
        for val in ["true", "TRUE", "  True  ", "\tTrUe\n"]:
            result = checker._convertToBoolean(None, "fieldName", val, False, False)
            self.assertTrue(result)

        # 4. String "false" variants
        for val in ["false", "FALSE", "  False  ", "\nFaLsE\t"]:
            result = checker._convertToBoolean(None, "fieldName", val, False, False)
            self.assertFalse(result)

        # 5. Invalid string with report_unexpected_exception=False → no log
        result = checker._convertToBoolean(None, "fieldName", "notbool", False, True)
        self.assertEqual(result, "")

        # Assert exactly one error was logged
        self.assertEqual(len(checker.errorRecords), 1)

        err = checker.errorRecords[0]
        self.assertEqual(err["field"], "fieldName")
        self.assertEqual(err["value"], "notbool")
        # message should include our literal
        self.assertIn("Invalid String Data", err["message"])
        # and code should default to UNEXPECTED_EXCEPTION
        self.assertEqual(err["code"], exception_messages.RECORD_CHECK_FAILED)

    #check for dose sequence
    def test_convert_to_dose(self):
        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)
        # Valid dose
        for dose in [1, 4, 9]:
            with self.subTest(dose=dose):
                result = checker._convertToDose("DOSESEQUENCE", "DOSE_AMOUNT", dose, False, True)
                self.assertEqual(result, dose)

        # Invalid dose
        invalid_doses = [10, 10.1, 100, 9.0001]
        for dose in invalid_doses:
            with self.subTest(dose=dose):
                result = checker._convertToDose("DOSESEQUENCE", "DOSE_AMOUNT", dose, False, True)
                self.assertEqual(result, "", f"Expected empty string for invalid dose {dose}")

    def clear_table(self):
        scan = self.table.scan()
        with self.table.batch_writer() as batch:
            for item in scan.get("Items", []):
                batch.delete_item(Key={"PK": item["PK"]})
        result = self.table.scan()
        items = result.get("Items", [])

    if __name__ == "__main__":
        unittest.main()
