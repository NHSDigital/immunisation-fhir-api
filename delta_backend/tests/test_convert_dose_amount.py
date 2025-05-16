import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from delta_converter import Converter

class TestDoseAmountTypeUriToFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_dose_amount_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get("DOSE_AMOUNT"), expected_result)
        
    def test_dose_amount_value_exists(self):
        self.request_json_data["doseQuantity"] = {
            "value": 0.5,
            "code": "ml",
            "unit": "milliliter"
        }
        self._run_dose_amount_test(expected_result=0.5)
        
    def test_dose_amount_value_missing(self):
        self.request_json_data["doseQuantity"] = {
            "code": "ml",
            "unit": "milliliter"
            # 'value' intentionally omitted
        }
        self._run_dose_amount_test(expected_result="")
        
    def test_dose_amount_section_missing(self):
        self.request_json_data.pop("doseQuantity", "")
        self._run_dose_amount_test(expected_result="")