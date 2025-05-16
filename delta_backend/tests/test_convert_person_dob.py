import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from delta_converter import Converter

class TestPersonDob(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
    
    
    def _run_person_dob_test(self, expected_site_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get("PERSON_DOB"), expected_site_code)
        
    
    