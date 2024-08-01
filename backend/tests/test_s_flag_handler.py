"""Tests for s_flag_handler"""

import unittest
from copy import deepcopy

from src.s_flag_handler import handle_s_flag
from tests.utils.generic_utils import load_json_data


class TestSFlagHandler(unittest.TestCase):
    """Test that s_flag_handler removes the required fields for patients marked as Restricted"""

    def test_s_flag_handler(self):
        """Test that personal info is removed for Restricted patients, and not removed for Unrestricted patients"""
        input_immunization = load_json_data("completed_covid19_immunization_event.json")
        filtered_output = load_json_data("completed_covid19_immunization_event_filtered_for_s_flag.json")
        restricted_patient = {"meta": {"security": [{"code": "R"}]}}
        unrestricted_patient = {"meta": {"security": [{"code": "U"}]}}

        self.assertEqual(handle_s_flag(deepcopy(input_immunization), restricted_patient), filtered_output)
        self.assertEqual(handle_s_flag(deepcopy(input_immunization), unrestricted_patient), input_immunization)
