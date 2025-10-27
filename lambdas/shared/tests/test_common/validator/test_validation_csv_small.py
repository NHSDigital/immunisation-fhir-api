import json
import unittest
from pathlib import Path

from common.validator.validator import Validator


class TestValidator(unittest.TestCase):
    """
    Unit tests for the CSV validation logic using the Validator class with a small CSV schema.
    """

    def setUp(self):
        self.parent_folder = Path(__file__).parent
        schema_file_path = self.parent_folder / "test_schemas/test_small_schema.json"
        with open(schema_file_path) as file:
            self.schema = json.load(file)

    def test_run_validation_csv_success(self):
        good_file_path = self.parent_folder / "sample_data/test_small_ok.csv"
        validator = Validator(self.schema)
        error_report = validator.validate_csv(good_file_path, False, True, True)
        self.assertTrue(error_report == [])

    def test_run_validation_csv_fails(self):
        bad_file_path = self.parent_folder / "sample_data/test_small_nok.csv"
        validator = Validator(self.schema)
        error_report = validator.validate_csv(bad_file_path, False, True, True)
        self.assertTrue(error_report != [])
