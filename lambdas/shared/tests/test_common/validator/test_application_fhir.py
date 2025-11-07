# Test application file
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from common.validator.error_report.error_reporter import build_error_report
from common.validator.validator import Validator
from tests.test_common.validator.testing_utils.csv_fhir_utils import parse_test_file


class TestApplication(unittest.TestCase):
    def setUp(self):
        validation_folder = Path(__file__).resolve().parent
        self.FHIRFilePath = validation_folder / "sample_data/vaccination2.json"
        self.schemaFilePath = validation_folder / "test_schemas/test_schema.json"
        self.fhir_resources = None

    def test_validation(self):
        start = time.time()

        SchemaFile = parse_test_file(self.schemaFilePath)
        self.fhir_resources = parse_test_file(self.FHIRFilePath)
        fhir_parser = Mock()
        fhir_parser.get_fhir_value.return_value = "2025-11-06T12:00:00Z"

        validator = Validator(SchemaFile)  # FHIR File Path not needed
        error_list = validator.validate_fhir(self.fhir_resources, True, True, True)
        error_report = build_error_report(
            "25a8cc4d-1875-4191-ac6d-2d63a0ebc64b", fhir_parser, error_list
        )  # include eventID if known

        failed_validation = validator.has_validation_failed(error_list)

        if len(error_list) > 0:
            print(error_list)
        else:
            print("Validated Successfully")
        print(error_report)

        if failed_validation:
            print("Validation failed due to a critical validation failure...")
        else:
            print("Validation Successful, see reports for details")

        end = time.time()
        print("Time Taken : ")
        print(end - start)
