# Test application file
import json
import unittest
from pathlib import Path

from common.validator.validator import Validator

CSV_HEADER = (
    "academic_year,time_period,time_identifier,geographic_level,"
    "country_code,country_name,region_code,region_name,new_la_code,la_name,"
    "old_la_code,school_type,num_schools,enrolments,present_sessions,overall_attendance,"
    "approved_educational_activity,overall_absence,authorised_absence,unauthorised_absence,"
    "late_sessions,possible_sessions,reason_present_am,reason_present_pm,reason_present,"
    "reason_l_present_late_before_registers_closed"
)

schema_data_folder = Path(__file__).parent / "schemas"
schemaFilePath = schema_data_folder / "test_school_schema.json"


class TestValidator(unittest.TestCase):
    def setUp(self):
        with open(schemaFilePath) as JSON:
            SchemaFile = json.load(JSON)
        self.validator = Validator(SchemaFile)

    def test_run_validation_csv_row_success(self):
        good_row = (
            "202223,202223,Spring term,Local authority,E92000001,England,E12000004,"
            "East Midlands,E06000016,Leicester,856,Primary,66,23057,2367094,"
            "2380687,13593,166808,99826,66982,34090,2547495,1157575,1180365,2337940,29154"
        )
        error_report = self.validator.validate_csv_row(good_row, CSV_HEADER, True, True, True)
        self.assertTrue(error_report == [])

    def test_run_validation_csv_row_failure(self):
        # empty time_period
        bad_row = (
            "202223,,Spring term,Local authority,E92000001,England,E12000004,"
            "East Midlands,E06000016,Leicester,856,Primary,66,23057,2367094,"
            "2380687,13593,166808,99826,66982,34090,2547495,1157575,1180365,2337940,29154"
        )
        error_report = self.validator.validate_csv_row(bad_row, CSV_HEADER, True, True, True)
        self.assertTrue(len(error_report) > 0)
        error = error_report[0]
        self.assertEqual(error.id, "check2")
        self.assertEqual(error.message, "Value not empty failure")
        self.assertEqual(error.name, "Time Period Not Empty Check")
        self.assertEqual(error.details, "Value is empty, not as expected")
