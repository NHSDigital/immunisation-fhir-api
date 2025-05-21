import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestUniqueIdUri(unittest.TestCase):

    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)

    def _run_unique_id_uri(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(ConversionFieldName.UNIQUE_ID_URI), expected_result)

    def test_unique_id_uri_present(self):
        """Should extract UNIQUE_ID_URI when identifier[0].system exists"""
        self._run_unique_id_uri(expected_result="https://supplierABC/identifiers/vacc")

    def test_unique_id_uri_missing_system(self):
        """Should return None when identifier[0].system is missing"""
        self.request_json_data["identifier"][0].pop("system", "")
        self._run_unique_id_uri(expected_result="")

    def test_unique_id_uri_empty_identifier_list(self):
        """Should return None when identifier list is empty"""
        self.request_json_data["identifier"] = []
        self._run_unique_id_uri(expected_result="")

    def test_unique_id_uri_missing_identifier_section(self):
        """Should return None when identifier section is missing entirely"""
        self.request_json_data.pop("identifier", "")
        self._run_unique_id_uri(expected_result="")
