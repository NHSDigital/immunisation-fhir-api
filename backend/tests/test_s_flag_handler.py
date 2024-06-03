"""Tests for s_flag_handler"""

import unittest
from copy import deepcopy

from src.s_flag_handler import handle_s_flag
from tests.utils.generic_utils import load_json_data


class TestRemovePersonalInfo(unittest.TestCase):
    """Test that s_flag_handler removes personal info where necessary"""

#TO DO - AMEND TO NEW JSON FILES AND ELEMENT LOCATIONS   
    def data_for_sflag_tests(self):
        '''JSON data used in test cases'''
        self.input_immunization = load_json_data("completed_covid19_immunization_event.json")
        self.expected_output = load_json_data("completed_covid19_filtered_immunization_event.json")
        self.patient = {"meta": {"security": [{"code":"R"}]}}
        
    def test_remove_personal_info(self):
        """Test that personal info is removed for s_flagged patients"""
        self.data_for_sflag_tests()
        result = handle_s_flag(self.input_immunization, self.patient)
        self.assertEqual(result, self.expected_output)

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

    def test_change_postcode_for_s_flag(self):
        #TO DO - AMEND TO NEW JSON LOCATIONS
        '''Test that postalcode is changed to "ZZ99 3CZ" for s flagged patients'''
        self.data_for_sflag_tests()   
        for record in self.expected_output.get("contained",[]):
            if record["resourceType" == "Patient"]:
                record["address"][0]["postalCode"] == "zz99 3CZ"
        
        result = handle_s_flag(self.input_immunization, self.patient)
        self.assertEqual(result, self.expected_output)

    # def test_change_postcode_for_s_flag(self):
    #     #TO DO - AMEND TO NEW JSON LOCATIONS
    #     '''Test that postalcode is changed to "ZZ99 3CZ" for s flagged patients'''
    #     self.data_for_sflag_tests()   
    #     result = handle_s_flag(self.input_immunization, self.patient)
    #     expected_postalcode = next( record["address"][0].get("postalCode", None)
    #     for record in self.expected_output.get("Resource", []).get("contained", [])
    #     if record.get("resourceType","") == "patient"
    #     )
        
    #     result_postalcode = next( record["address"][0].get("postalCode", None)
    #     for record in result.get("contained", [])
    #     if record["resourceType"] == "patient"
    #     )
    #     self.assertEqual(result_postalcode, expected_postalcode)
