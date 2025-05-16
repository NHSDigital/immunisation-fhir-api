import copy
import json
import unittest
from tests.utils_for_converter_tests import ValuesForTests
from delta_converter import Converter


class TestPractitionerForeNameToFlatJson(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def test_practitioner_forename_multiple_names_official(self):
        """Test case where multiple name instances exist, and one has use=official with period covering vaccination date"""
        self.request_json_data["contained"][0]["name"] = [
            {
                "family": "Doe",
                "given": ["Johnny"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2022-01-01"},
            },
            {
                "family": "Doe",
                "given": ["John"],
                "use": "official",
                "period": {"start": "2020-01-01", "end": "2021-01-01"},
            },
            {
                "family": "Doe",
                "given": ["Manny"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
            {
                "family": "Doe",
                "given": ["Davis"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
        ]
        expected_forename = "Manny"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        self.request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_forename = "John"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_single_name(self):
        """Test case where only one name instance exists"""
        self.request_json_data["contained"][0]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_forename = "Alex"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_no_official_but_current_not_old(self):
        """Test case where no official name is present, but a current name with use!=old exists at vaccination date"""
        self.request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Chris"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_fallback_to_first_name(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        self.request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "given": ["Elliot"], "use": "nickname"},
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Elliot"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_multiple_given_names_concatenation(self):
        """Test case where the selected name has multiple given names"""
        self.request_json_data["contained"][0]["name"] = [
            {
                "family": "Doe",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
            {
                "family": "Doe",
                "given": ["Alice", "Marie"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2022-12-31"},
            },
        ]
        expected_forename = "Alice Marie"
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_given_missing(self):
        """Test case where the selected name has multiple given names"""
        self.request_json_data["contained"][0]["name"] = [
            {"family": "Doe", "use": "official", "period": {"start": "2021-01-01", "end": "2022-12-31"}}
        ]
        expected_forename = ""
        self._run_practitioner_test(expected_forename)

    def test_practitioner_forename_empty(self):
        """Test case where the selected name has multiple given names"""
        self.request_json_data["contained"][0]["name"] = []
        expected_forename = ""
        self._run_practitioner_test(expected_forename)

    def _run_practitioner_test(self, expected_forename):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json["PERFORMING_PROFESSIONAL_FORENAME"], expected_forename)

