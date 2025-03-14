from typing import List
from decimal import Decimal

from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, valid_nhs_number_with_s_flag
from utils.immunisation_api import ImmunisationApi
from utils.resource import generate_imms_resource, generate_filtered_imms_resource
from utils.mappings import VaccineTypes


class SFlagBaseTest(ImmunizationBaseTest):
    """Parent class with helper for storing immunisation events in the IEDS"""

    def store_imms(self, imms_api: ImmunisationApi, patient_is_restricted: bool) -> dict:
        """
        Store an immunisation event in the IEDS using valid_nhs_number_with_s_flag if patient is restricted, or
        valid_nhs_number_1 otherwise
        """
        nhs_number = valid_nhs_number_with_s_flag if patient_is_restricted else valid_nhs_number1
        imms = generate_imms_resource(nhs_number=nhs_number, vaccine_type=VaccineTypes.covid_19)
        return self.create_immunization_resource(imms_api, imms)


class TestGetSFlagImmunization(SFlagBaseTest):
    """Test that sensitive data is filtered out for a READ if and only if the patient is s-flagged"""
    
    def test_get_not_s_flagged_imms(self):
        """Test that sensitive data is not filtered out for a READ when the patient is not s-flagged"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms = self.store_imms(imms_api, patient_is_restricted=False)
                read_imms = imms_api.get_immunization_by_id(imms).json(parse_float=Decimal)
                expected_response = generate_filtered_imms_resource(
                    crud_operation_to_filter_for="READ",
                    filter_for_s_flag=False,
                    nhs_number=valid_nhs_number1,
                )
                expected_response["id"] = read_imms["id"]
                self.assertEqual(read_imms, expected_response)


class TestSearchSFlagImmunization(SFlagBaseTest):
    """Test that sensitive data is filtered out for a SEARCH if and only if the patient is s-flagged"""

    def test_search_s_flagged_imms(self):
        """Test that sensitive data is filtered out for a SEARCH when the patient is s-flagged"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms1 = self.store_imms(imms_api, patient_is_restricted=True)
                imms2 = self.store_imms(imms_api, patient_is_restricted=True)
                # When
                response = imms_api.search_immunizations(valid_nhs_number_with_s_flag, VaccineTypes.covid_19).json(
                    parse_float=Decimal
                )
                # Then
                hit_imms = self.filter_my_imms_from_search_result(response, imms1, imms2)
                for hit_imm in hit_imms:
                    expected_response = generate_filtered_imms_resource(
                        crud_operation_to_filter_for="SEARCH",
                        filter_for_s_flag=True,
                        nhs_number=valid_nhs_number_with_s_flag,
                    )
                    expected_response["id"] = hit_imm["id"]
                    # Patient reference will have been updated by the API, identifier value is randomly assigned by
                    # create_an_imms_obj, so update the expected response dict accordingly
                    expected_response["patient"]["reference"] = hit_imm["patient"]["reference"]
                    expected_response["identifier"][0]["value"] = hit_imm["identifier"][0]["value"]
                    self.assertEqual(hit_imm, expected_response)

    def test_search_not_s_flagged_imms(self):
        """Test that sensitive data is not filtered out for a SEARCH when the patient is not s-flagged"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms_id_1 = self.store_imms(imms_api, patient_is_restricted=False)
                imms_id_2 = self.store_imms(imms_api, patient_is_restricted=False)
                # When
                response = imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.covid_19).json(
                    parse_float=Decimal
                )
                # Then
                hit_imms = self.filter_my_imms_from_search_result(response, imms_id_1, imms_id_2)
                for hit_imm in hit_imms:
                    expected_response = generate_filtered_imms_resource(
                        crud_operation_to_filter_for="SEARCH",
                        filter_for_s_flag=False,
                        nhs_number=valid_nhs_number1,
                    )
                    expected_response["id"] = hit_imm["id"]
                    # Patient reference will have been updated by the API, identifier value is randomly assigned by
                    # create_an_imms_obj, so update the expected response dict accordingly
                    expected_response["patient"]["reference"] = hit_imm["patient"]["reference"]
                    expected_response["identifier"][0]["value"] = hit_imm["identifier"][0]["value"]
                    self.assertEqual(hit_imm, expected_response)

    @staticmethod
    def filter_my_imms_from_search_result(search_body: dict, *my_ids) -> List[dict]:
        """Returns all immunisation entries for which the id is in my_ids"""
        return [entry["resource"] for entry in search_body["entry"] if entry["resource"]["id"] in my_ids]
