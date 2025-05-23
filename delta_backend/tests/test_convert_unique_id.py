import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestUniqueId(unittest.TestCase):

    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)

    def _run_unique_id(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(ConversionFieldName.UNIQUE_ID), expected_result)

    def test_unique_id_present(self):
        """Should extract UNIQUE_ID when identifier[0].value exists"""
        self._run_unique_id(expected_result="ACME-vacc123456")

    def test_unique_id_missing_value(self):
        """Should return None when identifier[0].value is missing"""
        self.request_json_data["identifier"][0].pop("value", "")
        self._run_unique_id(expected_result="")

    def test_unique_id_empty_identifier_list(self):
        """Should return None when identifier list is empty"""
        self.request_json_data["identifier"] = []
        self._run_unique_id(expected_result="")

    def test_unique_id_missing_identifier_section(self):
        """Should return None when identifier section is missing entirely"""
        self.request_json_data.pop("identifier", "")
        self._run_unique_id(expected_result="")
