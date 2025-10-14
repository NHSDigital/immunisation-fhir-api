# Test application file
from pathlib import Path
from common.validator.validator import Validator
import json
import time
import unittest


class TestApplication(unittest.TestCase):
    def setUp(self):

        fhir_data_folder = Path("./data")
        self.FHIRFilePath = fhir_data_folder / "vaccination.json"

        self.schema_data_folder = Path("./schemas")
        self.schemaFilePath = self.schema_data_folder / "schema.json"

    def test_validation(self):

        DATA_TYPE = 'FHIR'

        start = time.time()

        # get the JSON of the schema, changed to cope with elasticache
        with open(self.schemaFilePath, 'r') as JSON:
            SchemaFile = json.load(JSON)

        # get the FHIR Data as JSON
        with open(self.FHIRFilePath, 'r') as JSON:
            FHIRData = json.load(JSON)

        validator = Validator(self.FHIRFilePath, FHIRData, SchemaFile, '', '',
                              DATA_TYPE)  # FHIR File Path not needed
        error_list = validator.run_validation(True, True, True)
        error_report = validator.build_error_report(
            '25a8cc4d-1875-4191-ac6d-2d63a0ebc64b')  # include eventID if known

        failed_validation = validator.has_validation_failed()

        self.assertTrue(len(error_list) == 0,
                        f"Validation failed. Errors: {error_list}")
        self.assertTrue(len(error_report['errors']) == 0,
                        f"Validation failed. Errors: {error_report['errors']}")

        self.assertFalse(failed_validation, 'Validation failed')

        end = time.time()
        print('Time Taken : ')
        print(end - start)
