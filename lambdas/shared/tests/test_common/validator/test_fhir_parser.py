# Test application file
import unittest
from pathlib import Path

from common.validator.parsers.fhir_parser import FHIRParser
from tests.test_common.validator.testing_utils.csv_fhir_utils import parse_test_file


class TestParse(unittest.TestCase):
    def setUp(self):
        self.fhir_data_folder = Path(__file__).parent / "sample_data"
        fhirFilePath = self.fhir_data_folder / "vaccination.json"
        self.fhir_data = parse_test_file(fhirFilePath)

    def test_parse_fhir_key_exists(self):
        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_data(self.fhir_data)
        my_value = fhir_parser.get_fhir_value_list("vaccineCode|coding|0|code")
        self.assertEqual(my_value, ["42223111000001107"])

    def test_parse_fhir_key_not_exists(self):
        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_data(self.fhir_data)
        my_value = fhir_parser.get_fhir_value_list("vaccineCode|coding|1")
        self.assertEqual(my_value, [""])
        my_value = fhir_parser.get_fhir_value_list("vaccineCode|coding|1|codes")
        self.assertEqual(my_value, [""])
