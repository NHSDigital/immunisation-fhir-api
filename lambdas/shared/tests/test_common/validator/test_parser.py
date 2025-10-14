# Test application file
import unittest
from pathlib import Path

from common.validator.parsers.fhir_parser import FHIRParser


class TestParse(unittest.TestCase):

    def setUp(self):
        self.fhir_data_folder = Path(__file__).parent / "data"

    def test_parse_fhir_key_exists(self):

        fhirFilePath = self.fhir_data_folder / "vaccination.json"

        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_file(fhirFilePath)
        my_value = fhir_parser.get_key_value('vaccineCode|coding|0|code')
        self.assertEqual(my_value, ['42223111000001107'])

    def test_parse_fhir_key_not_exists(self):

        fhirFilePath = self.fhir_data_folder / "vaccination.json"

        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_file(fhirFilePath)
        my_value = fhir_parser.get_key_value('vaccineCode|coding|1')
        self.assertEqual(my_value, [''])
        my_value = fhir_parser.get_key_value('vaccineCode|coding|1|codes')
        self.assertEqual(my_value, [''])
