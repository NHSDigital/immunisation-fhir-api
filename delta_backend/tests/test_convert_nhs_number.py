import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter

class TestNHSNumberToFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_nhs_number_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get("NHS_NUMBER"), expected_result)
        
    def test_nhs_number_valid(self):
        # Sample already contains valid NHS number in the Patient resource
        self._run_nhs_number_test(expected_result="9000000009")
        
    def test_nhs_number_invalid_system(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource["identifier"][0]["system"] = "http://wrong-system.org"
        self._run_nhs_number_test(expected_result="")
        
    def test_nhs_number_missing_identifier(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource.pop("identifier", "")
        self._run_nhs_number_test(expected_result="")
        
    def test_nhs_number_missing_patient(self):
        self.request_json_data["contained"] = [
            r for r in self.request_json_data.get("contained", [])
            if r.get("resourceType") != "Patient"
        ]
        self._run_nhs_number_test(expected_result="")