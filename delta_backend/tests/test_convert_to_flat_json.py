import json
import unittest
import os
import time
from decimal import Decimal
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock
from moto import mock_dynamodb, mock_sqs
from boto3 import resource as boto3_resource, client as boto3_client
from tests.utils_for_converter_tests import ValuesForTests, ErrorValuesForTests
from botocore.config import Config
from pathlib import Path
from SchemaParser import SchemaParser
from Converter import Converter
from ConversionChecker import ConversionChecker


MOCK_ENV_VARS = {
    "AWS_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
    "DELTA_TABLE_NAME": "immunisation-batch-internal-dev-audit-test-table",
    "SOURCE": "test-source",
}
request_json_data = ValuesForTests.json_data
with patch.dict("os.environ", MOCK_ENV_VARS):
    from delta import handler, Converter
    from Converter import imms, ErrorRecords


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
        self.assertIsInstance(imms_data, str)
        self.assertGreater(len(imms_data), 0)

        # Check Imms JSON structure matches exactly
        self.assertEqual(imms_data, str(expected_imms), "Imms data does not match expected JSON structure")

        for key, expected_value in expected_values.items():
            self.assertIn(key, filtered_items[0], f"{key} is missing")
            self.assertEqual(filtered_items[0][key], expected_value, f"{key} mismatch")

    def test_fhir_converter_json_direct_data(self):
        """it should convert fhir json data to flat json"""
        imms.clear()
        json_data = json.dumps(ValuesForTests.json_data)

        start = time.time()

        FHIRConverter = Converter(json_data)
        FlatFile = FHIRConverter.runConversion(ValuesForTests.json_data, False, True)

        flatJSON = json.dumps(FlatFile)
        expected_imms_value = deepcopy(ValuesForTests.expected_imms)  # UPDATE is currently the default action-flag
        expected_imms = json.dumps(expected_imms_value)
        self.assertEqual(flatJSON, expected_imms)

        errorRecords = FHIRConverter.getErrorRecords()
        # print(flatJSON)

        if len(errorRecords) > 0:
            print("Converted With Errors")
        else:
            print("Converted Successfully")

        end = time.time()
        print(end - start)

    def test_fhir_converter_json_error_scenario(self):
        """it should convert fhir json data to flat json - error scenarios"""
        error_test_cases = [ErrorValuesForTests.missing_json, ErrorValuesForTests.json_dob_error]

        for test_case in error_test_cases:
            imms.clear()
            json_data = json.dumps(test_case)

            start = time.time()

            FHIRConverter = Converter(json_data)
            FlatFile = FHIRConverter.runConversion(ValuesForTests.json_data, False, True)

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

    def test_conversionCount(self):
        parser = SchemaParser()
        schema_data = {"conversions": [{"conversion": "type1"}, {"conversion": "type2"}, {"conversion": "type3"}]}
        parser.parseSchema(schema_data)
        self.assertEqual(parser.conversionCount(), 3)

    def test_getConversion(self):
        parser = SchemaParser()
        schema_data = {"conversions": [{"conversion": "type1"}, {"conversion": "type2"}, {"conversion": "type3"}]}
        parser.parseSchema(schema_data)
        self.assertEqual(parser.getConversion(1), {"conversion": "type2"})

    # TODO revisit and amend if necessary

    @patch("Converter.FHIRParser")
    def test_fhir_parser_exception(self, mock_fhir_parser):
        # Mock FHIRParser to raise an exception
        mock_fhir_parser.side_effect = Exception("FHIR Parsing Error")
        converter = Converter(fhir_data="some_data")

        response = converter.runConversion("somedata")

        # Check if the error message was added to ErrorRecords
        self.assertEqual(len(response), 2)
        self.assertIn("FHIR Parser Unexpected exception", converter.getErrorRecords()[0]["message"])
        self.assertEqual(converter.getErrorRecords()[0]["code"], 0)

    @patch("Converter.SchemaParser")
    def test_schema_parser_exception(self, mock_schema_parser):
        # Mock SchemaParser to raise an exception
        mock_schema_parser.side_effect = Exception("Schema Parsing Error")
        converter = Converter(fhir_data="some_data")

        response = converter.runConversion("some_data")

        # Check if the error message was added to ErrorRecords
        self.assertEqual(len(response), 2)
        self.assertIn(
            "FHIR Parser Unexpected exception [JSONDecodeError]: Expecting value: line 1 column 1 (char 0)",
            converter.getErrorRecords()[0]["message"],
        )
        self.assertEqual(converter.getErrorRecords()[0]["code"], 0)

    @patch("Converter.ConversionChecker")
    def test_conversion_checker_exception(self, mock_conversion_checker):
        # Mock ConversionChecker to raise an exception
        mock_conversion_checker.side_effect = Exception("Conversion Checking Error")
        converter = Converter(fhir_data="some_data")

        response = converter.runConversion(ValuesForTests.json_data)

        # Check if the error message was added to ErrorRecords
        self.assertEqual(len(converter.getErrorRecords()), 1)
        self.assertIn(
            "FHIR Parser Unexpected exception [JSONDecodeError]: Expecting value: line 1 column 1 (char 0)",
            converter.getErrorRecords()[0]["message"],
        )
        self.assertEqual(converter.getErrorRecords()[0]["code"], 0)

    @patch("Converter.SchemaParser.getConversions")
    def test_get_conversions_exception(self, mock_get_conversions):
        # Mock getConversions to raise an exception
        mock_get_conversions.side_effect = Exception("Error while getting conversions")
        converter = Converter(fhir_data="some_data")

        response = converter.runConversion(ValuesForTests.json_data)

        # Check if the error message was added to ErrorRecords
        self.assertEqual(len(converter.getErrorRecords()), 3)
        self.assertIn(
            "FHIR Parser Unexpected exception [JSONDecodeError]: Expecting value: line 1 column 1 (char 0)",
            converter.getErrorRecords()[0]["message"],
        )
        self.assertEqual(converter.getErrorRecords()[0]["code"], 0)

    @patch("Converter.SchemaParser.getConversions")
    @patch("Converter.FHIRParser.getKeyValue")
    def test_conversion_exceptions(self, mock_get_key_value, mock_get_conversions):
        mock_get_conversions.side_effect = Exception("Error while getting conversions")
        mock_get_key_value.side_effect = Exception("Key value retrieval failed")
        ErrorRecords.clear()
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

        response = converter.runConversion(ValuesForTests.json_data)

        error_records = converter.getErrorRecords()
        self.assertEqual(len(error_records), 1)

        self.assertIn(
            "FHIR Parser Unexpected exception [JSONDecodeError]: Expecting value: line 1 column 1 (char 0)",
            error_records[0]["message"],
        )
        self.assertEqual(error_records[0]["code"], 0)

    @patch("ConversionChecker.LookUpData")
    def test_convert_to_not_empty(self, MockLookUpData):

        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        result = checker._convertToNotEmpty(None, "fieldName", "Some data", False, True)
        self.assertEqual(result, "Some data")

        result = checker._convertToNotEmpty(None, "fieldName", "", False, True)
        self.assertEqual(result, "")

    @patch("ConversionChecker.LookUpData")
    def test_convert_to_nhs_number(self, MockLookUpData):

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

    @patch("ConversionChecker.LookUpData")
    def test_convert_to_date(self, MockLookUpData):
        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        valid_date = "2022-01-01"
        result = checker._convertToDate("%Y%m%d", "fieldName", valid_date, False, True)
        self.assertEqual(result, "20220101")
        
        invalid_date = "invalid_date"
        result = checker._convertToDate("format:%Y%m%d", "fieldName", invalid_date, False, True)
        self.assertEqual(result, "Unexpected format: invalid_date")

        # Test for error case with exception
        result = checker._convertToDate("%Y%m%d", "fieldName", None, False, True)
        self.assertEqual(result, "")
  
    @patch("ConversionChecker.LookUpData")
    def test_convert_to_date_time(self, MockLookUpData):
        dataParser = Mock()

        checker = ConversionChecker(dataParser, summarise=False, report_unexpected_exception=True)

        valid_date_time = "2022-01-01T12:00:00+00:00"
        result = checker._convertToDateTime("%Y%m%dT%H%M%S", "fieldName", valid_date_time, False, True)
        self.assertEqual(result, "20220101T120000")

        valid_csv_utc = "2022-01-01T13:28:17+00:00"
        result = checker._convertToDateTime("format:csv-utc", "fieldName", valid_csv_utc, False, True)
        self.assertEqual(result, "20220101T13281700")

        invalid_date_time = "invalid_date_time"
        result = checker._convertToDateTime("format:%Y%m%dT%H%M%S", "fieldName", invalid_date_time, False, True)
        self.assertEqual(result, "Unexpected format: invalid_date_time")
        
        # Empty input returns blank
        result = checker._convertToDateTime("format:%Y%m%dT%H%M%S", "fieldName", "", False, True)
        self.assertEqual(result, "")

    #check for dose sequence
    @patch("ConversionChecker.LookUpData")
    def test_convert_to_dose(self, MockLookUpData):
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


class TestPersonForeNameToFlatJson(unittest.TestCase):
    def test_person_forename_multiple_names_official(self):
        """Test case where multiple name instances exist, and one has use=official with period covering vaccination date"""
        request_json_data["contained"][1]["name"] = [
            {
                "family": "Doe",
                "given": ["Johnny"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2022-01-01"},
            },
            {
                "family": "Doe",
                "given": ["John"],
                "use": "official",
                "period": {"start": "2020-01-01", "end": "2021-01-01"},
            },
            {
                "family": "Doe",
                "given": ["Manny"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
            {
                "family": "Doe",
                "given": ["Davis"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
        ]
        expected_forename = "Manny"
        self._run_test(expected_forename)

    def test_person_forename_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_forename = "John"
        self._run_test(expected_forename)

    def test_person_forename_single_name(self):
        """Test case where only one name instance exists"""
        request_json_data["contained"][1]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_forename = "Alex"
        self._run_test(expected_forename)

    def test_person_forename_no_official_but_current_not_old(self):
        """Test case where no official name is present, but a current name with use!=old exists at vaccination date"""
        request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Chris"
        self._run_test(expected_forename)

    def test_person_forename_fallback_to_first_name(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["Elliot"], "use": "nickname"},
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Elliot"
        self._run_test(expected_forename)

    def test_person_forename_multiple_given_names_concatenation(self):
        """Test case where the selected name has multiple given names"""
        request_json_data["contained"][1]["name"] = [
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
            {
                "family": "Doe",
                "given": ["Alice", "Marie"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2022-12-31"},
            },
        ]
        expected_forename = "Alice Marie"
        self._run_test(expected_forename)

    def _run_test(self, expected_forename):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0]["PERSON_FORENAME"], expected_forename)


class TestPersonSurNameToFlatJson(unittest.TestCase):

    def test_person_surname_multiple_names_official(self):
        """Test case where multiple name instances exist, and one has use=official with period covering vaccination date"""
        request_json_data["contained"][1]["name"] = [
            {
                "family": "Doe",
                "given": ["Johnny"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2022-01-01"},
            },
            {
                "family": "Manny",
                "given": ["John"],
                "use": "official",
                "period": {"start": "2020-01-01", "end": "2021-01-01"},
            },
            {
                "family": "Davis",
                "given": ["Manny"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
            {
                "family": "Johnny",
                "given": ["Davis"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
        ]
        expected_forename = "Davis"
        self._run_test_surname(expected_forename)

    def test_person_surname_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        request_json_data["contained"][1]["name"] = [
            {"family": "Manny", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_forename = "Manny"
        self._run_test_surname(expected_forename)

    def test_person_surname_single_name(self):
        """Test case where only one name instance exists"""
        request_json_data["contained"][1]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_forename = "Doe"
        self._run_test_surname(expected_forename)

    def test_person_surname_no_official_but_current_not_old(self):
        """Test case where no official name is present, but a current name with use!=old exists at vaccination date"""
        request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Manny",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Manny"
        self._run_test_surname(expected_forename)

    def test_person_surname_fallback_to_first_name(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["Elliot"], "use": "nickname"},
            {
                "family": "Manny",
                "given": ["John"],
                "use": "old",
                "period": {"start": "2018-01-01", "end": "2020-12-31"},
            },
            {
                "family": "Davis",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Doe"
        self._run_test_surname(expected_forename)

    def _run_test_surname(self, expected_forename):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0]["PERSON_SURNAME"], expected_forename)


class TestPersonPostalCodeToFlatJson(unittest.TestCase):
    def test_person_postal_code_single_address(self):
        """Test case where only one address instance exists"""
        request_json_data["contained"][1]["address"] = [{"postalCode": "AB12 3CD"}]
        expected_postal_code = "AB12 3CD"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_ignore_address_without_postal_code(self):
        """Test case where multiple addresses exist, but one lacks a postalCode"""
        request_json_data["contained"][1]["address"] = [
            {"use": "home", "type": "physical"},
            {"postalCode": "XY99 8ZZ", "use": "home", "type": "physical"},
        ]
        expected_postal_code = "XY99 8ZZ"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_ignore_non_current_addresses(self):
        """Test case where multiple addresses exist, but some are not current at the vaccination date"""
        request_json_data["contained"][1]["address"] = [
            {
                "postalCode": "AA11 1AA",
                "use": "home",
                "type": "physical",
                "period": {"start": "2018-01-01", "end": "2020-12-31"},
            },
            {
                "postalCode": "BB22 2BB",
                "use": "home",
                "type": "physical",
                "period": {"start": "2021-01-01", "end": "2023-12-31"},
            },
            {
                "postalCode": "BB22 2BC",
                "use": "home",
                "type": "physical",
                "period": {"start": "2021-01-01", "end": "2024-12-31"},
            },
        ]
        expected_postal_code = "BB22 2BB"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_select_home_type_not_postal(self):
        """Test case where a home address with type!=postal should be selected"""
        request_json_data["contained"][1]["address"] = [
            {"postalCode": "CC33 3CC", "use": "old", "type": "physical"},
            {"postalCode": "DD44 4DD", "use": "home", "type": "physical"},
            {"postalCode": "DD44 4DP", "use": "home", "type": "physical"},
            {"postalCode": "EE55 5EE", "use": "temp", "type": "postal"},
        ]
        expected_postal_code = "DD44 4DD"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_select_first_non_old_type_not_postal(self):
        """Test case where an address with use!=old and type!=postal should be selected"""
        request_json_data["contained"][1]["address"] = [
            {"postalCode": "FF66 6FF", "use": "old", "type": "physical"},
            {"postalCode": "GG77 7GG", "use": "temp", "type": "physical"},
            {"postalCode": "GG77 7GI", "use": "temp", "type": "physical"},
            {"postalCode": "HH88 8HH", "use": "old", "type": "postal"},
        ]
        expected_postal_code = "GG77 7GG"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_fallback_first_non_old(self):
        """Test case where the first address with use!=old is selected"""
        request_json_data["contained"][1]["address"] = [
            {"postalCode": "II99 9II", "use": "old", "type": "postal"},
            {"postalCode": "JJ10 1JJ", "use": "old", "type": "physical"},
            {"postalCode": "KK20 2KK", "use": "billing", "type": "postal"},
        ]
        expected_postal_code = "KK20 2KK"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_default_to_ZZ99_3CZ(self):
        """Test case where no valid postalCode is found, should default to ZZ99 3CZ"""
        request_json_data["contained"][1]["address"] = [
            {"use": "old", "type": "postal"},
            {"use": "temp", "type": "postal"},
        ]
        expected_postal_code = "ZZ99 3CZ"
        self._run_postal_code_test(expected_postal_code)

    def _run_postal_code_test(self, expected_postal_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0]["PERSON_POSTCODE"], expected_postal_code)


class TestPersonSiteCodeToFlatJson(unittest.TestCase):
    def test_site_code_single_performer(self):
        """Test case where only one performer instance exists"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        {"actor": {"value": "OTHER123"}},
        expected_site_code = "B0C4P"
        self._run_site_code_test(expected_site_code)

    def test_site_code_performer_type_organization_only(self):
        """Test case where performer has type=organization and system=https://fhir.nhs.uk/Id/ods-organization-code with more than one instance"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code2"
        self._run_site_code_test(expected_site_code)

    def test_site_code_performer_type_organization(self):
        """Test case where performer has type=organization but no NHS system"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organizatdion-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code2"
        self._run_site_code_test(expected_site_code)

    def test_site_code_performer_type_without_oraganisation(self):
        """Test case where performer has type=organization but no NHS system"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code4"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code1"
        self._run_site_code_test(expected_site_code)

    def test_site_code_fallback_to_first_performer(self):
        """Test case where no performers match specific criteria, fallback to first instance"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code2"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code1"
        self._run_site_code_test(expected_site_code)

    def _run_site_code_test(self, expected_site_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0].get("SITE_CODE"), expected_site_code)


class TestPersonSiteUriToFlatJson(unittest.TestCase):
    def test_site_uri_single_performer(self):
        """Test case where only one performer instance exists"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        {"actor": {"value": "OTHER123"}},
        expected_site_uri = "https://fhir.nhs.uk/Id/ods-organization-code"
        self._run_site_uri_test(expected_site_uri)

    def test_site_code_performer_type_organization_only(self):
        """Test case where performer has type=organization and system=https://fhir.nhs.uk/Id/ods-organization-code with more than one instance"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-codes", "value": "code1"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_uri = "https://fhir.nhs.uk/Id/ods-organization-code"
        self._run_site_uri_test(expected_site_uri)

    def test_site_code_performer_type_organization(self):
        """Test case where performer has type=organization but no NHS system"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organizatdion-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_uri = "https://fhir.nhs.uk/Id/ods-nhs-code"
        self._run_site_uri_test(expected_site_uri)

    def test_site_code_fallback_to_first_performer(self):
        """Test case where no performers match specific criteria, fallback to first instance"""
        request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code2"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_uri = "https://fhir.nhs.uk/Id/ods-nhs-code"
        self._run_site_uri_test(expected_site_uri)

    def _run_site_uri_test(self, expected_site_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0].get("SITE_CODE_TYPE_URI"), expected_site_code)


class TestPractitionerForeNameToFlatJson(unittest.TestCase):
    def test_practitioner_forename_multiple_names_official(self):
        """Test case where multiple name instances exist, and one has use=official with period covering vaccination date"""
        request_json_data["contained"][0]["name"] = [
            {
                "family": "Doe",
                "given": ["Johnny"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2022-01-01"},
            },
            {
                "family": "Doe",
                "given": ["John"],
                "use": "official",
                "period": {"start": "2020-01-01", "end": "2021-01-01"},
            },
            {
                "family": "Doe",
                "given": ["Manny"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
            {
                "family": "Doe",
                "given": ["Davis"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
        ]
        expected_forename = "Manny"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_forename = "John"
        self._run_practitioner_test(expected_forename)

    def test_Practitioner_forename_single_name(self):
        """Test case where only one name instance exists"""
        request_json_data["contained"][0]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_forename = "Alex"
        self._run_practitioner_test(expected_forename)

    def test_Practitioner_forename_no_official_but_current_not_old(self):
        """Test case where no official name is present, but a current name with use!=old exists at vaccination date"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Chris"
        self._run_practitioner_test(expected_forename)

    def test_Practitioner_forename_fallback_to_first_name(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["Elliot"], "use": "nickname"},
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Elliot"
        self._run_practitioner_test(expected_forename)

    def test_Practitioner_forename_multiple_given_names_concatenation(self):
        """Test case where the selected name has multiple given names"""
        request_json_data["contained"][0]["name"] = [
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
            {
                "family": "Doe",
                "given": ["Alice", "Marie"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2022-12-31"},
            },
        ]
        expected_forename = "Alice Marie"
        self._run_practitioner_test(expected_forename)

    def test_Practitioner_forename_given_missing(self):
        """Test case where the selected name has multiple given names"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "use": "official", "period": {"start": "2021-01-01", "end": "2022-12-31"}}
        ]
        expected_forename = ""
        self._run_practitioner_test(expected_forename)

    def test_Practitioner_forename_empty(self):
        """Test case where the selected name has multiple given names"""
        request_json_data["contained"][0]["name"] = []
        expected_forename = ""
        self._run_practitioner_test(expected_forename)

    def _run_practitioner_test(self, expected_forename):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0]["PERFORMING_PROFESSIONAL_FORENAME"], expected_forename)


class TestPractitionerSurNameToFlatJson(unittest.TestCase):
    def test_practitioner_surname_multiple_names_official(self):
        """Test case where multiple name instances exist, and one has use=official with period covering vaccination date"""
        request_json_data["contained"][0]["name"] = [
            {
                "family": "Doe",
                "given": ["Johnny"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2022-01-01"},
            },
            {
                "family": "Manny",
                "given": ["John"],
                "use": "official",
                "period": {"start": "2020-01-01", "end": "2021-01-01"},
            },
            {
                "family": "Davis",
                "given": ["Manny"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
            {
                "family": "Johnny",
                "given": ["Davis"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
        ]
        expected_forename = "Davis"
        self._run_test_practitioner_surname(expected_forename)

    def test_practitioner_surname_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Manny", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_forename = "Manny"
        self._run_test_practitioner_surname(expected_forename)

    def test_practitioner_surname_single_name(self):
        """Test case where only one name instance exists"""
        request_json_data["contained"][0]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_forename = "Doe"
        self._run_test_practitioner_surname(expected_forename)

    def test_practitioner_surname_no_official_but_current_not_old(self):
        """Test case where no official name is present, but a current name with use!=old exists at vaccination date"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Manny",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Manny"
        self._run_test_practitioner_surname(expected_forename)

    def test_practitioner_surname_fallback_to_first_name(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["Elliot"], "use": "nickname"},
            {
                "family": "Manny",
                "given": ["John"],
                "use": "old",
                "period": {"start": "2018-01-01", "end": "2020-12-31"},
            },
            {
                "family": "Davis",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Doe"
        self._run_test_practitioner_surname(expected_forename)

    def test_practitioner_surname_empty(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        request_json_data["contained"][0]["name"] = [
            {"given": ["Elliot"], "use": "nickname"},
            {
                "family": "Manny",
                "given": ["John"],
                "use": "old",
                "period": {"start": "2018-01-01", "end": "2020-12-31"},
            },
            {
                "family": "Davis",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = ""
        self._run_test_practitioner_surname(expected_forename)

    def test_contained_empty(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        request_json_data["contained"][0]["name"] = []
        expected_forename = ""
        self._run_test_practitioner_surname(expected_forename)

    def _run_test_practitioner_surname(self, expected_forename):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(request_json_data))
        flat_json = self.converter.runConversion(request_json_data, False, True)
        self.assertEqual(flat_json[0]["PERFORMING_PROFESSIONAL_SURNAME"], expected_forename)

    if __name__ == "__main__":
        unittest.main()