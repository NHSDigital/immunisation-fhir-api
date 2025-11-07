import unittest
from pathlib import Path

from tests.test_common.validator.testing_utils.csv_fhir_utils import parse_test_file


class TestValidator(unittest.TestCase):
    """
    Unit tests for the Full CSV File validation. Obtains the schema from a file and runs
    validation on sample CSV files to ensure correct validation behavior.
    """

    def setUp(self):
        self.parent_folder = Path(__file__).parent
        schema_file_path = self.parent_folder / "test_schemas/test_small_schema.json"
        self.schema = parse_test_file(schema_file_path)

    # def test_run_validation_csv_success(self):
    #     good_file_path = self.parent_folder / "sample_data/valid_csv_data.csv"
    #     validator = Validator(self.schema)
    #     error_report = validator.validate_csv(good_file_path, False, True, True)
    #     self.assertTrue(error_report == [])

    # def test_run_validation_csv_fails(self):
    #     bad_file_path = self.parent_folder / "sample_data/invalid_csv_data.csv"
    #     validator = Validator(self.schema)
    #     error_report = validator.validate_csv(bad_file_path, False, True, True)
    #     self.assertTrue(error_report != [])
