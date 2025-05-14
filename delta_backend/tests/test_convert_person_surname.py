import copy
import json
import unittest
from tests.utils_for_converter_tests import ValuesForTests
from Converter import Converter


class TestPersonSurNameToFlatJson(unittest.TestCase):

    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
    
    def test_person_surname_multiple_names_official(self):
        """Test case where multiple name instances exist, and one has use=official with period covering vaccination date"""
        self.request_json_data["contained"][1]["name"] = [
            {
                "family": "Doe",
                "given": ["Johnny"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2022-01-01"},
            },
            {
                "family": "Manny",
                "given": ["John"],
                "use": "official",
                "period": {"start": "2020-01-01", "end": "2021-01-01"},
            },
            {
                "family": "Davis",
                "given": ["Manny"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
            {
                "family": "Johnny",
                "given": ["Davis"],
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2021-02-09"},
            },
        ]
        expected_forename = "Davis"
        self._run_test_surname(expected_forename)

    def test_person_surname_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        self.request_json_data["contained"][1]["name"] = [
            {"family": "Manny", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_forename = "Manny"
        self._run_test_surname(expected_forename)

    def test_person_surname_single_name(self):
        """Test case where only one name instance exists"""
        self.request_json_data["contained"][1]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_forename = "Doe"
        self._run_test_surname(expected_forename)

    def test_person_surname_no_official_but_current_not_old(self):
        """Test case where no official name is present, but a current name with use!=old exists at vaccination date"""
        self.request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["John"], "use": "old", "period": {"start": "2018-01-01", "end": "2020-12-31"}},
            {
                "family": "Manny",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Manny"
        self._run_test_surname(expected_forename)

    def test_person_surname_fallback_to_first_name(self):
        """Test case where no names match the previous conditions, fallback to first available name"""
        self.request_json_data["contained"][1]["name"] = [
            {"family": "Doe", "given": ["Elliot"], "use": "nickname"},
            {
                "family": "Manny",
                "given": ["John"],
                "use": "old",
                "period": {"start": "2018-01-01", "end": "2020-12-31"},
            },
            {
                "family": "Davis",
                "given": ["Chris"],
                "use": "nickname",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            },
        ]
        expected_forename = "Doe"
        self._run_test_surname(expected_forename)

    def _run_test_surname(self, expected_forename):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.runConversion(self.request_json_data, False, True)
        self.assertEqual(flat_json["PERSON_SURNAME"], expected_forename)
