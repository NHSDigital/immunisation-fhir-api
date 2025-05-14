import copy
import json
import unittest
from tests.utils_for_converter_tests import ValuesForTests
from Converter import Converter


class TestPersonSiteCodeToFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def test_site_code_single_performer(self):
        """Test case where only one performer instance exists"""
        self.request_json_data["performer"] = [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        {"actor": {"value": "OTHER123"}},
        expected_site_code = "B0C4P"
        self._run_site_code_test(expected_site_code)

    def test_site_code_performer_type_organization_only(self):
        """Test case where performer has type=organization and system=https://fhir.nhs.uk/Id/ods-organization-code with more than one instance"""
        self.request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code2"
        self._run_site_code_test(expected_site_code)

    def test_site_code_performer_type_organization(self):
        """Test case where performer has type=organization but no NHS system"""
        self.request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organizatdion-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code2"
        self._run_site_code_test(expected_site_code)

    def test_site_code_performer_type_without_oraganisation(self):
        """Test case where performer has type=organization but no NHS system"""
        self.request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code2"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "code4"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code3"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code1"
        self._run_site_code_test(expected_site_code)

    def test_site_code_fallback_to_first_performer(self):
        """Test case where no performers match specific criteria, fallback to first instance"""
        self.request_json_data["performer"] = [
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhs-code", "value": "code1"},
                }
            },
            {
                "actor": {
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-nhss-code", "value": "code2"},
                }
            },
            {"actor": {"reference": "#Pract1"}},
        ]
        expected_site_code = "code1"
        self._run_site_code_test(expected_site_code)

    def _run_site_code_test(self, expected_site_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.runConversion(self.request_json_data, False, True)
        self.assertEqual(flat_json.get("SITE_CODE"), expected_site_code)
