"""Tests for s_flag_handler"""

import unittest
from copy import deepcopy

from src.s_flag_handler import handle_s_flag
from tests.utils.generic_utils import load_json_data


class TestRemovePersonalInfo(unittest.TestCase):
    """Test that s_flag_handler removes personal info where necessary"""

    def test_remove_personal_info(self):
        """Test that personal info is removed for s_flagged patients"""
        input_immunization = load_json_data("completed_covid19_immunization_event.json")
        expected_output = load_json_data("completed_covid19_filtered_immunization_event.json")
        patient = {"meta": {"security": [{"code": "R"}]}}

        result = {'Resource':handle_s_flag(input_immunization, patient)}

        self.assertEqual(result, expected_output)

    def test_when_missing_patient_fields_do_not_remove_personal_info(self):
        """Test that personal info is not removed when no patient fields are present"""
        input_immunization = load_json_data("completed_covid19_immunization_event.json")
        expected_output = deepcopy(input_immunization)
        patient = {"meta": {}}

        result = handle_s_flag(input_immunization, patient)

        self.assertEqual(result, expected_output)
