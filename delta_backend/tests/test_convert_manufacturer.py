import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter

class TestVaccineManufacturer(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_vaccine_manufacturer_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get("VACCINE_MANUFACTURER"), expected_result)
        
    def test_vaccine_manufacturer_present(self):
        """Should return the manufacturer name when present"""
        self.request_json_data["manufacturer"] = {"display": "AstraZeneca Ltd"}
        self._run_vaccine_manufacturer_test(expected_result="AstraZeneca Ltd")

    def test_vaccine_manufacturer_missing_display(self):
        """Should return None when manufacturer.display is missing"""
        self.request_json_data["manufacturer"] = {}
        self._run_vaccine_manufacturer_test(expected_result="")

    def test_vaccine_manufacturer_missing_entirely(self):
        """Should return None when manufacturer is missing entirely"""
        self.request_json_data.pop("manufacturer", None)
        self._run_vaccine_manufacturer_test(expected_result="")

    def test_vaccine_manufacturer_empty_string(self):
        """Should return None when manufacturer.display is an empty string"""
        self.request_json_data["manufacturer"] = {"display": ""}
        self._run_vaccine_manufacturer_test(expected_result="")
        
    