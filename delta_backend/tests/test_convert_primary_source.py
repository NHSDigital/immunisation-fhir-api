import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestPrimarySourceFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_primary_source_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(ConversionFieldName.PRIMARY_SOURCE), expected_result)
    
    def test_primary_source_true(self):
        """Should return True when primarySource is true"""
        self.request_json_data["primarySource"] = True
        self._run_primary_source_test(expected_result=True)

    def test_primary_source_false(self):
        """Should return False when primarySource is false"""
        self.request_json_data["primarySource"] = False
        self._run_primary_source_test(expected_result=False)

    def test_primary_source_is_string_true(self):
        """Should return True when primarySource is true"""
        self.request_json_data["primarySource"] = "true"
        self._run_primary_source_test(expected_result=True)

    def test_primary_source_is_string_false(self):
        """Should return False when primarySource is false"""
        self.request_json_data["primarySource"] = "false"
        self._run_primary_source_test(expected_result=False)
        
    def test_primary_source_missing(self):
        """Should return None when primarySource is missing"""
        self.request_json_data.pop("primarySource", None)
        self._run_primary_source_test(expected_result="")
    