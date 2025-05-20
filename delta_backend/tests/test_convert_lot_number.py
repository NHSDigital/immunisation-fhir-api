import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter

class TestBatchNumber(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_batch_number_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get("BATCH_NUMBER"), expected_result)
        
    def test_batch_number_present(self):
        """Should extract lotNumber when present"""
        self.request_json_data["lotNumber"] = "4120Z001"
        self._run_batch_number_test(expected_result="4120Z001")

    def test_batch_number_missing(self):
        """Should return None when lotNumber is missing"""
        self.request_json_data.pop("lotNumber", None)
        self._run_batch_number_test(expected_result="")

    def test_batch_number_empty_string(self):
        """Should return None when lotNumber is an empty string"""
        self.request_json_data["lotNumber"] = ""
        self._run_batch_number_test(expected_result="")
            
        