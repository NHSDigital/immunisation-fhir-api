# Test application file
import unittest
from pathlib import Path

from common.validator.validator import Validator
from test_common.validator.testing_utils.constants import CSV_HEADER, CSV_VALUES
from tests.test_common.validator.testing_utils.csv_fhir_utils import build_row, parse_test_file

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
        valid_rows = build_row(CSV_HEADER, CSV_VALUES)
        error_report = self.validator.validate_csv_row(valid_rows, CSV_HEADER, True, True, True)
        print(f"Error Report: {error_report}")
        self.assertEqual(error_report, [])

    def test_run_validation_on_invalid_csv_row(self):
        invalid_rows = build_row(CSV_HEADER, {**CSV_VALUES, "NHS_NUMBER": ""})
        error_report = self.validator.validate_csv_row(invalid_rows, CSV_HEADER, True, True, True)
        print(f"Error Report: {error_report}")
        self.assertTrue(len(error_report) > 0)
        messages = [(e.name, e.message, e.details) for e in error_report]
        expected_error = (
            "NHS Number Not Empty Check",
            "Value not empty failure",
            "Value is empty, not as expected",
        )
        self.maxDiff = None
        print(f"Error Report: {error_report}")
        print(f"Messages: {messages}")
        print(f"Expected Error: {expected_error}")
        self.assertIn(expected_error, messages)
