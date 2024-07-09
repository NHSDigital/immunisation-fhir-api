"""Tests for s_flag_handler"""

import unittest
from copy import deepcopy

from src.s_flag_handler import handle_s_flag
from tests.utils.generic_utils import load_json_data


class TestRemovePersonalInfo(unittest.TestCase):
    """Test that s_flag_handler removes personal info where necessary"""

    def data_for_sflag_tests(self):
        '''JSON data used in test cases'''
        self.input_immunization = load_json_data("completed_covid19_immunization_event_filtered_for_read.json")
        self.expected_output = load_json_data("completed_covid19_immunization_event_filtered_for_s_flag_and_read.json")
        self.patient = {"meta": {"security": [{"code":"R"}]}}
        result = handle_s_flag(self.input_immunization, self.patient)
        
        print(result)
        print(F"OUTPUT: {self.expected_output}")
        
    # def test_remove_personal_info(self):
    #     """Test that personal info is removed for s_flagged patients"""
    #     self.data_for_sflag_tests()
    #     result = handle_s_flag(self.input_immunization, self.patient)
    #     self.assertEqual(result, self.expected_output)
        

    def test_when_missing_patient_fields_do_not_remove_personal_info(self):
        """Test that personal info is not removed when no patient fields are present"""
        self.data_for_sflag_tests()
        patient = {"meta": {}}
        result = handle_s_flag(self.input_immunization, patient)
        self.assertEqual(result, self.input_immunization)
        
    def test_when_security_code_is_not_r(self):
        self.data_for_sflag_tests()
        """Test that personal info is not removed when security code is not r (s flagged code)"""
        patient_not_flagged = {"meta": {"security": [{"code":"S"}]}}
        result = handle_s_flag(self.input_immunization, patient_not_flagged)
        self.assertEqual(result, self.input_immunization)

    def test_remove_location(self):
        '''Test that location is removed for s flagged patients'''
        self.data_for_sflag_tests()
        result = handle_s_flag(self.input_immunization, self.patient)
        self.assertNotIn ("location", result)
        
    def test_remove_reportOrigin(self):
        '''Test that reportOrigin is removed for s flagged patients'''
        self.data_for_sflag_tests()
        result = handle_s_flag(self.input_immunization, self.patient)
        self.assertNotIn ("reportOrigin", result)
        
    def test_remove_patient_address(self):
        """Test that patient address is anonymized for s flagged patients"""
        self.data_for_sflag_tests()
        result = handle_s_flag(self.input_immunization, self.patient)
        patient_data = result.get("contained", [])[1]
        self.assertEqual(patient_data["address"][0]["postalCode"], "ZZ99 3CZ")
        
    # def test_amend_display_to_null(self):
    #     '''Test that display field is amended to null'''
    #     self.data_for_sflag_tests()
    #     result = handle_s_flag(self.input_immunization, self.patient)
    #     consent_answers = result["contained"][2]["item"][1]["answer"]
    #     for answer in consent_answers:
    #         if "valueCoding" in answer and "display" in answer["valueCoding"]:
    #             self.assertIsNone(answer["valueCoding"]["display"])