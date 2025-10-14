# Test application file
import json
import time
import unittest
from pathlib import Path

from common.validator.validator import Validator

# TODO this needs success and fail cases


class TestApplication(unittest.TestCase):
    def setUp(self):

        validation_folder = Path(__file__).parent
        self.FHIRFilePath = validation_folder / "data/vaccination2.json"
        self.schemaFilePath = validation_folder / "schemas/schema.json"

    def test_validation(self):
        start = time.time()

        # get the JSON of the schema, changed to cope with elasticache
        with open(self.schemaFilePath) as JSON:
            SchemaFile = json.load(JSON)

        validator = Validator(SchemaFile)  # FHIR File Path not needed
        error_list = validator.validate_fhir(self.FHIRFilePath, True, True, True)
        error_report = validator.build_error_report('25a8cc4d-1875-4191-ac6d-2d63a0ebc64b')  # include eventID if known

        failed_validation = validator.has_validation_failed()

        if len(error_list) > 0:
            print(error_list)
        else:
            print('Validated Successfully')

        print('--------------------------------------------------------------------')
        print(error_report)
        print('--------------------------------------------------------------------')

        if (failed_validation):
            print('Validation failed due to a critical validation failure...')
        else:
            print('Validation Successful, see reports for details')

        end = time.time()
        print('Time Taken : ')
        print(end - start)
