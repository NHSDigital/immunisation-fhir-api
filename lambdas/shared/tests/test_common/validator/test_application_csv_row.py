# Test application file
import json
import unittest
from pathlib import Path

from test_common.validator.testing_utils.constants import CSV_HEADER
from test_common.validator.testing_utils.constants import CSV_VALUES

from common.validator.validator import Validator

schema_data_folder = Path(__file__).parent / "test_schemas"
schemaFilePath = schema_data_folder / "test_schema.json"


class TestValidator(unittest.TestCase):
    """
    Unit tests for the CSV row validation logic using the Validator class.
    """

    @staticmethod
    def build_row(header: str, csv_file: dict) -> str:
        """
        Construct a CSV row string from the provided csv_file.
        Any missing header columns get empty string values.
        """
        cols = header.split(",")
        return ",".join(str(csv_file.get(col, "")) for col in cols)

    def setUp(self):
        with open(schemaFilePath, encoding="utf-8") as file:
            schema_file = json.load(file)
        self.validator = Validator(schema_file)

    def test_run_validation_on_valid_csv_row(self):
        valid_rows = self.build_row(CSV_HEADER, CSV_VALUES)
        error_report = self.validator.validate_csv_row(valid_rows, CSV_HEADER, True, True, True)
        self.assertEqual(error_report, [])

    def test_run_validation_on_invalid_csv_row(self):
        invalid_rows = self.build_row(CSV_HEADER, {**CSV_VALUES, "NHS_NUMBER": ""})
        error_report = self.validator.validate_csv_row(invalid_rows, CSV_HEADER, True, True, True)
        self.assertTrue(len(error_report) > 0)
        messages = [(e.name, e.message, e.details) for e in error_report]
        expected_error = (
            "NHS Number Not Empty Check",
            "Value not empty failure",
            "Value is empty, not as expected",
        )
        self.assertIn(expected_error, messages)
