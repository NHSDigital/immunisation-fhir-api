import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestLocationCodeTypeUri(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_location_code_type_uri_test(self, expected_uri):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(ConversionFieldName.LOCATION_CODE_TYPE_URI), expected_uri)

    def test_location_code_type_uri_when_present(self):
        """Should return the correct LOCATION_CODE_TYPE_URI from input"""
        self.request_json_data["location"] = {
            "identifier": {
                "system": "https://custom-url.org/LocationSystem",
                "value": "ABC123"
            },
            "type": "Location"
        }
        self._run_location_code_type_uri_test("https://custom-url.org/LocationSystem")

    def test_location_code_type_uri_when_location_missing(self):
        """Should return default LOCATION_CODE_TYPE_URI when location is missing"""
        self.request_json_data.pop("location", None)
        self._run_location_code_type_uri_test("https://fhir.nhs.uk/Id/ods-organization-code")

    def test_location_code_type_uri_when_identifier_missing(self):
        """Should return default LOCATION_CODE_TYPE_URI when identifier is missing"""
        self.request_json_data["location"] = {
            "type": "Location"
        }
        self._run_location_code_type_uri_test("https://fhir.nhs.uk/Id/ods-organization-code")

    def test_location_code_type_uri_when_system_missing(self):
        """Should return default LOCATION_CODE_TYPE_URI when system is missing"""
        self.request_json_data["location"] = {
            "identifier": {
                "value": "ABC123"
            },
            "type": "Location"
        }
        self._run_location_code_type_uri_test("https://fhir.nhs.uk/Id/ods-organization-code")
