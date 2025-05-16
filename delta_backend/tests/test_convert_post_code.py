import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from delta_converter import Converter


class TestPersonPostalCodeToFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def test_person_postal_code_single_address(self):
        """Test case where only one address instance exists"""
        self.request_json_data["contained"][1]["address"] = [{"postalCode": "AB12 3CD"}]
        expected_postal_code = "AB12 3CD"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_ignore_address_without_postal_code(self):
        """Test case where multiple addresses exist, but one lacks a postalCode"""
        self.request_json_data["contained"][1]["address"] = [
            {"use": "home", "type": "physical"},
            {"postalCode": "XY99 8ZZ", "use": "home", "type": "physical"},
        ]
        expected_postal_code = "XY99 8ZZ"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_ignore_non_current_addresses(self):
        """Test case where multiple addresses exist, but some are not current at the vaccination date"""
        self.request_json_data["contained"][1]["address"] = [
            {
                "postalCode": "AA11 1AA",
                "use": "home",
                "type": "physical",
                "period": {"start": "2018-01-01", "end": "2020-12-31"},
            },
            {
                "postalCode": "BB22 2BB",
                "use": "home",
                "type": "physical",
                "period": {"start": "2021-01-01", "end": "2023-12-31"},
            },
            {
                "postalCode": "BB22 2BC",
                "use": "home",
                "type": "physical",
                "period": {"start": "2021-01-01", "end": "2024-12-31"},
            },
        ]
        expected_postal_code = "BB22 2BB"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_select_home_type_not_postal(self):
        """Test case where a home address with type!=postal should be selected"""
        self.request_json_data["contained"][1]["address"] = [
            {"postalCode": "CC33 3CC", "use": "old", "type": "physical"},
            {"postalCode": "EE55 5EE", "use": "temp", "type": "postal"},
            {"postalCode": "DD44 4DD", "use": "home", "type": "physical"},
            {"postalCode": "DD44 4DP", "use": "home", "type": "physical"},
        ]
        expected_postal_code = "DD44 4DD"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_select_first_non_old_type_not_postal(self):
        """Test case where an address with use!=old and type!=postal should be selected"""
        self.request_json_data["contained"][1]["address"] = [
            {"postalCode": "FF66 6FF", "use": "old", "type": "physical"},
            {"postalCode": "GG77 7GG", "use": "temp", "type": "physical"},
            {"postalCode": "HH88 8HH", "use": "old", "type": "postal"},
            {"postalCode": "GG77 7GI", "use": "temp", "type": "physical"},
        ]
        expected_postal_code = "GG77 7GG"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_fallback_first_non_old(self):
        """Test case where the first address with use!=old is selected"""
        self.request_json_data["contained"][1]["address"] = [
            {"postalCode": "II99 9II", "use": "old", "type": "postal"},
            {"postalCode": "JJ10 1JJ", "use": "old", "type": "physical"},
            {"postalCode": "KK20 2KK", "use": "billing", "type": "postal"},
        ]
        expected_postal_code = "KK20 2KK"
        self._run_postal_code_test(expected_postal_code)

    def test_person_postal_code_default_to_ZZ99_3CZ(self):
        """Test case where no valid postalCode is found, should default to ZZ99 3CZ"""
        self.request_json_data["contained"][1]["address"] = [
            {"use": "old", "type": "postal"},
            {"use": "temp", "type": "postal"},
        ]
        expected_postal_code = "ZZ99 3CZ"
        self._run_postal_code_test(expected_postal_code)

    def _run_postal_code_test(self, expected_postal_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json["PERSON_POSTCODE"], expected_postal_code)

