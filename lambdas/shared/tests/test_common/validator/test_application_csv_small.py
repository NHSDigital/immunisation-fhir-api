# Test application file
import json
import unittest
from pathlib import Path

from common.validator.validator import Validator


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.parent_folder = Path(__file__).parent
        schema_file_path = self.parent_folder / "schemas/test_small_schema.json"
        with open(schema_file_path) as JSON:
            self.schema = json.load(JSON)

    def test_run_validation_csv_success(self):
        good_file_path = self.parent_folder / "data/test_small_ok.csv"
        validator = Validator(self.schema)
        error_report = validator.validate_csv(good_file_path, False, True, True)
        self.assertTrue(error_report == [])

    def test_run_validation_csv_fails(self):
        bad_file_path = self.parent_folder / "data/test_small_nok.csv"
        validator = Validator(self.schema)
        error_report = validator.validate_csv(bad_file_path, False, True, True)
        self.assertTrue(error_report != [])
