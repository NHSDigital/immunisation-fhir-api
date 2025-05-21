import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestLocationCode(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _run_location_code_test(self, expected_site_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(ConversionFieldName.LOCATION_CODE), expected_site_code)
    
    def test_location_code_when_present(self):
        """Should return the correct LOCATION_CODE from input"""
        self.request_json_data["location"] = {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                "value": "ABC123"
            },
            "type": "Location"
        }
        self._run_location_code_test("ABC123")

    def test_location_code_when_missing(self):
        """Should return 'X99999' when location is missing"""
        self.request_json_data.pop("location", None)
        self._run_location_code_test("X99999")

    def test_location_code_when_identifier_missing(self):
        """Should return 'X99999' when location.identifier is missing"""
        self.request_json_data["location"] = {
            "type": "Location"
        }
        self._run_location_code_test("X99999")

    def test_location_code_when_value_missing(self):
        """Should return 'X99999' when location.identifier.value is missing"""
        self.request_json_data["location"] = {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code"
            },
            "type": "Location"
        }
        self._run_location_code_test("X99999")


            
        