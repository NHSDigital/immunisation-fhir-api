# Test application file
import json
import unittest
from pathlib import Path

from common.validator.validator import Validator

CSV_HEADER = (
    "NHS_NUMBER,PERSON_FORENAME,PERSON_SURNAME,SITE_CODE,"
    "PERFORMING_PROFESSIONAL_FORENAME,PERFORMING_PROFESSIONAL_SURNAME,PRIMARY_SOURCE,"
    "VACCINATION_PROCEDURE_CODE,VACCINATION_PROCEDURE_TERM,DOSE_SEQUENCE,"
    "VACCINE_PRODUCT_CODE,VACCINE_PRODUCT_TERM,VACCINE_MANUFACTURER,BATCH_NUMBER"
)

schema_data_folder = Path(__file__).parent / "schemas"
schemaFilePath = schema_data_folder / "test_schema.json"


class TestValidator(unittest.TestCase):
    @staticmethod
    def build_row(header: str, values: dict) -> str:
        cols = header.split(",")
        return ",".join(str(values.get(col, "")) for col in cols)

    def setUp(self):
        with open(schemaFilePath) as JSON:
            SchemaFile = json.load(JSON)
        self.validator = Validator(SchemaFile)

    def test_run_validation_csv_row_success(self):
        values = {
            "NHS_NUMBER": "9000000009",
            "PERSON_FORENAME": "JOHN",
            "PERSON_SURNAME": "DOE",
            "SITE_CODE": "RJ1",
            "PERFORMING_PROFESSIONAL_FORENAME": "ALICE",
            "PERFORMING_PROFESSIONAL_SURNAME": "SMITH",
            "PRIMARY_SOURCE": "true",
            "VACCINATION_PROCEDURE_CODE": "PROC123",
            "VACCINATION_PROCEDURE_TERM": "Procedure Term",
            "DOSE_SEQUENCE": 1,
            "VACCINE_PRODUCT_CODE": "VACC123",
            "VACCINE_PRODUCT_TERM": "Vaccine Term",
            "VACCINE_MANUFACTURER": "Manufacturer XYZ",
            "BATCH_NUMBER": "BATCH001",
        }
        good_row = self.build_row(CSV_HEADER, values)
        error_report = self.validator.validate_csv_row(good_row, CSV_HEADER, True, True, True)
        self.assertEqual(error_report, [])

    def test_run_validation_csv_row_failure(self):
        # With fieldNameFlat used for CSV, empty NHS_NUMBER should fail the NOTEMPTY check
        values = {
            "NHS_NUMBER": "",
            "PERSON_FORENAME": "JOHN",
            "PERSON_SURNAME": "DOE",
            "SITE_CODE": "RJ1",
            "PERFORMING_PROFESSIONAL_FORENAME": "ALICE",
            "PERFORMING_PROFESSIONAL_SURNAME": "SMITH",
            "PRIMARY_SOURCE": "true",
            "VACCINATION_PROCEDURE_CODE": "PROC123",
            "VACCINATION_PROCEDURE_TERM": "Procedure Term",
            "DOSE_SEQUENCE": 1,
            "VACCINE_PRODUCT_CODE": "VACC123",
            "VACCINE_PRODUCT_TERM": "Vaccine Term",
            "VACCINE_MANUFACTURER": "Manufacturer XYZ",
            "BATCH_NUMBER": "BATCH001",
        }
        bad_row = self.build_row(CSV_HEADER, values)
        error_report = self.validator.validate_csv_row(bad_row, CSV_HEADER, True, True, True)
        self.assertTrue(len(error_report) > 0)
        # Assert the NHS Number NOTEMPTY error is present
        messages = [(e.name, e.message, e.details) for e in error_report]
        self.assertIn(
            ("NHS Number Not Empty Check", "Value not empty failure", "Value is empty, not as expected"), messages
        )
