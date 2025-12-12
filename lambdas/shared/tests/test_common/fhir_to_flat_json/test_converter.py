import json
import unittest
from copy import deepcopy

from common.fhir_to_flat_json.converter import Converter
from test_common.fhir_to_flat_json.sample_values import ErrorValuesForTests, ValuesForTests


class TestConverter(unittest.TestCase):
    def test_fhir_converter_json_direct_data(self):
        """it should convert fhir json data to flat json"""
        json_data = json.dumps(ValuesForTests.json_data)

        fhir_converter = Converter(json_data)
        FlatFile = fhir_converter.run_conversion()

        flatJSON = json.dumps(FlatFile)
        expected_imms_value = deepcopy(ValuesForTests.expected_imms2)  # UPDATE is currently the default action-flag
        expected_imms = json.dumps(expected_imms_value)
        self.assertEqual(flatJSON, expected_imms)

        errorRecords = fhir_converter.get_error_records()

        self.assertEqual(len(errorRecords), 0)

    def test_fhir_converter_json_error_scenario_reporting_on(self):
        """it should convert fhir json data to flat json - error scenarios"""
        error_test_cases = [
            ErrorValuesForTests.missing_json,
            ErrorValuesForTests.json_dob_error,
        ]

        for test_case in error_test_cases:
            json_data = json.dumps(test_case)

            fhir_converter = Converter(json_data)
            fhir_converter.run_conversion()

            errorRecords = fhir_converter.get_error_records()

            # Check if bad data creates error records
            self.assertTrue(len(errorRecords) > 0)

    def test_fhir_converter_json_error_scenario_reporting_off(self):
        """it should convert fhir json data to flat json - error scenarios"""
        error_test_cases = [
            ErrorValuesForTests.missing_json,
            ErrorValuesForTests.json_dob_error,
        ]

        for test_case in error_test_cases:
            json_data = json.dumps(test_case)

            fhir_converter = Converter(json_data, report_unexpected_exception=False)
            fhir_converter.run_conversion()

            errorRecords = fhir_converter.get_error_records()

            # Check if bad data creates error records
            self.assertTrue(len(errorRecords) == 0)

    def test_fhir_converter_json_incorrect_data_scenario_reporting_on(self):
        """it should convert fhir json data to flat json - error scenarios"""

        with self.assertRaises(ValueError):
            fhir_converter = Converter(None)
            errorRecords = fhir_converter.get_error_records()
            self.assertTrue(len(errorRecords) > 0)

    def test_fhir_converter_json_incorrect_data_scenario_reporting_off(self):
        """it should convert fhir json data to flat json - error scenarios"""

        with self.assertRaises(ValueError):
            fhir_converter = Converter(None, report_unexpected_exception=False)
            errorRecords = fhir_converter.get_error_records()
            self.assertTrue(len(errorRecords) == 0)
