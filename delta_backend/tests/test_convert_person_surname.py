import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from converter import Converter
from common.mappings import ConversionFieldName

class TestPersonSurnameToFlatJson(unittest.TestCase):

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
        expected_surname = "Davis"
        self._run_test_surname(expected_surname)

    def test_person_surname_multiple_names_current(self):
        """Test case where no official name is present, but a name is current at the vaccination date"""
        self.request_json_data["contained"][1]["name"] = [
            {"family": "Manny", "given": ["John"], "period": {"start": "2020-01-01", "end": "2023-01-01"}},
            {"family": "Doe", "given": ["Johnny"], "use": "nickname"},
        ]
        expected_surname = "Manny"
        self._run_test_surname(expected_surname)

    def test_person_surname_single_name(self):
        """Test case where only one name instance exists"""
        self.request_json_data["contained"][1]["name"] = [{"family": "Doe", "given": ["Alex"], "use": "nickname"}]
        expected_surname = "Doe"
        self._run_test_surname(expected_surname)

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
        expected_surname = "Manny"
        self._run_test_surname(expected_surname)

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
        expected_surname = "Doe"
        self._run_test_surname(expected_surname)

    def test_person_surname_exists_only(self):
        """Test case where the selected name has multiple given names"""
        self.request_json_data["contained"][1]["name"] = [
            {
                "family": "Doe",
                "use": "official",
                "period": {"start": "2021-01-01", "end": "2023-01-01"},
            }
        ]
        self._run_test_surname("")

    def test_person_surname_exists_only_in_one_instance(self):
        """Test case where the selected name has multiple given names"""
        self.request_json_data["contained"][1]["name"] = [
            {
                "family": "Doe",
                "use": "official",
                "period": { "start": "2021-01-01", "end": "2023-01-01" }
            },
            {
                "family": "Smith",
                "given": ["Jack"],
                "use": "official",
                "period": { "start": "2021-01-01", "end": "2023-01-01" }
            }
        ]
        expected_surname = "Smith"
        self._run_test_surname(expected_surname)
        
    def _run_test_surname(self, expected_surname):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json[ConversionFieldName.PERSON_SURNAME], expected_surname)
