import copy
import json
import unittest
from utils_for_converter_tests import ValuesForTests
from delta_converter import Converter

class TestDateConversions(unittest.TestCase):
    
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
    
    def _run_date_test(self, flat_field_name, date):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(flat_field_name), date)

    def test_person_dob_converted_format(self):
        expected_dob = "19650228"  
        self._run_date_test("PERSON_DOB", expected_dob)
        
    def test_person_dob_missing(self):
        # Remove birthDate from Patient resource
        for res in self.request_json_data["contained"]:
            if res["resourceType"] == "Patient":
                res.pop("birthDate", "")
        self._run_date_test("PERSON_DOB", "")

    def test_person_dob_empty(self):
        # Set birthDate to empty string
        for res in self.request_json_data["contained"]:
            if res["resourceType"] == "Patient":
                res["birthDate"] = ""
        self._run_date_test("PERSON_DOB", "")
        
    def test_recorded_date_converted_format(self):
        self._run_date_test("RECORDED_DATE", "20210207")

    def test_recorded_date_missing(self):
        self.request_json_data.pop("recorded", "")
        self._run_date_test("RECORDED_DATE", "")

    def test_recorded_date_empty(self):
        self.request_json_data["recorded"] = ""
        self._run_date_test("RECORDED_DATE", "")
        
    def test_expiry_date_converted_format(self):
        self._run_date_test("EXPIRY_DATE", "20210702")

    def test_expiry_date_missing(self):
        self.request_json_data.pop("expirationDate", "")
        self._run_date_test("EXPIRY_DATE", "")

    def test_expiry_date_empty(self):
        self.request_json_data["expirationDate"] = ""
        self._run_date_test("EXPIRY_DATE", "")
        
    def test_date_and_time_with_utc(self):
        self.request_json_data["occurrenceDateTime"] = "2025-04-06T13:28:17+00:00"
        self._run_date_test("DATE_AND_TIME", "20250406T13281700")

    def test_date_and_time_with_bst(self):
        self.request_json_data["occurrenceDateTime"] = "2025-04-06T13:28:17+01:00"
        self._run_date_test("DATE_AND_TIME", "20250406T13281701")

    def test_date_and_time_without_timezone(self):
        self.request_json_data["occurrenceDateTime"] = "2025-04-06T13:28:17"
        self._run_date_test("DATE_AND_TIME", "20250406T13281700")

    def test_date_and_time_with_unsupported_offset(self):
        self.request_json_data["occurrenceDateTime"] = "2025-04-06T13:28:17+02:00"
        self._run_date_test("DATE_AND_TIME", "")

    def test_date_and_time_empty(self):
        self.request_json_data["occurrenceDateTime"] = ""
        self._run_date_test("DATE_AND_TIME", "")

    def test_date_and_time_invalid_format(self):
        self.request_json_data["occurrenceDateTime"] = "not-a-date"
        self._run_date_test("DATE_AND_TIME", "")
    