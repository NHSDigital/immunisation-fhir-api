# Test application file
import unittest

from pathlib import Path
from common.validator.parsers.fhir_parser import FHIRParser


class TestParse(unittest.TestCase):
    def test_parse_fhir_file(self):

        fhir_data_folder = Path("./data")
        fhirFilePath = fhir_data_folder / "vaccination.json"

        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_file(fhirFilePath)
        my_value = fhir_parser.get_key_value('vaccineCode|coding|0|code')
        self.assertEqual(my_value, ['42223111000001107'])
