# Test application file
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from common.validator.error_report.error_reporter import build_error_report
from common.validator.validator import Validator
from test_common.validator.testing_utils.constants import CSV_VALUES
from tests.test_common.validator.testing_utils.csv_fhir_utils import parse_test_file

schema_data_folder = Path(__file__).parent / "test_schemas"
schemaFilePath = schema_data_folder / "test_schema.json"


class TestValidator(unittest.TestCase):
    """
    Unit tests for the CSV row validation logic using the Validator class.
    """

    def setUp(self):
        self.validator = Validator(parse_test_file(schemaFilePath))
        self.maxDiff = None

    def test_run_validation_on_valid_csv_row(self):
        error_list = self.validator.validate_csv_row(CSV_VALUES, True, True, True)
        self.assertEqual(error_list, [])

    def test_run_validation_on_invalid_csv_row(self):
        invalid_rows = {**CSV_VALUES, "NHS_NUMBER": ""}
        error_list = self.validator.validate_csv_row(invalid_rows, True, True, True)

        self.assertTrue(len(error_list) > 0)
        messages = [(e.name, e.message, e.details) for e in error_list]
        expected_error = "NHS_NUMBER must be 10 characters"
        print(f"test_messages {messages}")
        self.assertTrue(any(expected_error in msg[2] for msg in messages))

        csv_parser = Mock()
        csv_parser.extract_field_value.return_value = "2025-11-06T12:00:00Z"
        error_report = build_error_report("25a8cc4d-1875-4191-ac6d-2d63a0ebc64b", csv_parser, error_list)

        failed_validation = self.validator.has_validation_failed(error_list)

        if len(error_list) > 0:
            start = time.time()

        if len(error_list) > 0:
            print(error_list)
        else:
            print("Validated CSV Successfully")
        print(error_report)

        if failed_validation:
            print("CSV Validation failed due to a critical validation failure...")
        else:
            print("CSV Validation Successful, see reports for details")

        end = time.time()
        print("Time Taken : ")
        print(end - start)
