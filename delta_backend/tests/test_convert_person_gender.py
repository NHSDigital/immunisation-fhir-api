import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestPersonGenderToFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json[ConversionFieldName.PERSON_GENDER_CODE], expected_result)
        
    def test_gender_male(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource["gender"] = "male"
        self._run_test(expected_result="1")
        
    def test_gender_female(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource["gender"] = "female"
        self._run_test(expected_result="2")
        
    def test_gender_other(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource["gender"] = "other"
        self._run_test(expected_result="9")
        
    def test_gender_unknown(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource["gender"] = "unknown"
        self._run_test(expected_result="0")
        
    def test_gender_missing(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource.pop("gender", "")
        self._run_test(expected_result="")
        
    def test_gender_invalid(self):
        for resource in self.request_json_data.get("contained", []):
            if resource.get("resourceType") == "Patient":
                resource["gender"] = "random"
        self._run_test(expected_result="")