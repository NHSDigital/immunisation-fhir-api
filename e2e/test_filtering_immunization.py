from typing import List
from decimal import Decimal

from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, valid_nhs_number_with_s_flag
from utils.immunisation_api import ImmunisationApi
from utils.resource import create_an_imms_obj, create_a_filtered_imms_obj, get_patient_id, get_vaccine_type
from utils.mappings import VaccineTypes


class SFlagBaseTest(ImmunizationBaseTest):
    """parent class with a set of assertion helpers"""

    def store_imms(self, imms_api: ImmunisationApi, patient_is_restricted: bool) -> dict:
        nhs_number = valid_nhs_number_with_s_flag if patient_is_restricted else valid_nhs_number1
        imms = create_an_imms_obj(nhs_number=nhs_number, vaccine_type=VaccineTypes.covid_19)
        return self.create_immunization_resource(imms_api, imms)


class TestGetSFlagImmunization(SFlagBaseTest):
    """An s-flagged patient contains sensitive data that must be filtered out by backend before being returned"""

    def test_get_s_flagged_imms(self):
        """it should filter certain fields if patient is s-flagged"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms_id = self.store_imms(imms_api, patient_is_restricted=True)
                read_imms = imms_api.get_immunization_by_id(imms_id).json(parse_float=Decimal)
                expected_response = create_a_filtered_imms_obj(
                    crud_operation_to_filter_for="READ",
                    filter_for_s_flag=True,
                    imms_id=read_imms["id"],
                    nhs_number=valid_nhs_number_with_s_flag,
                )
                self.assertEqual(read_imms, expected_response)

    def test_get_not_s_flagged_imms(self):
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms = self.store_imms(imms_api, patient_is_restricted=False)
                read_imms = imms_api.get_immunization_by_id(imms).json(parse_float=Decimal)
                expected_response = create_a_filtered_imms_obj(
                    crud_operation_to_filter_for="READ",
                    filter_for_s_flag=False,
                    imms_id=read_imms["id"],
                    nhs_number=valid_nhs_number1,
                )
                self.assertEqual(read_imms, expected_response)


class TestSearchSFlagImmunization(SFlagBaseTest):
    """An s-flagged patient contains sensitive data that must be filtered out by backend before being returned"""

    def test_search_s_flagged_imms(self):
        """it should perform filtering for all search results"""
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
                    expected_response = create_a_filtered_imms_obj(
                        crud_operation_to_filter_for="SEARCH",
                        filter_for_s_flag=True,
                        imms_id=hit_imm["id"],
                        nhs_number=valid_nhs_number_with_s_flag,
                    )
                    # Patient reference will have been updated by the API, identifier value is randomly assigned by
                    # create_an_imms_obj, so update the expected response dict accordingly
                    expected_response["patient"]["reference"] = hit_imm["patient"]["reference"]
                    expected_response["identifier"][0]["value"] = hit_imm["identifier"][0]["value"]
                    self.assertEqual(hit_imm, expected_response)

    def test_search_not_s_flagged_imms(self):
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
                    expected_response = create_a_filtered_imms_obj(
                        crud_operation_to_filter_for="SEARCH",
                        filter_for_s_flag=False,
                        imms_id=hit_imm["id"],
                        nhs_number=valid_nhs_number1,
                    )
                    # Patient reference will have been updated by the API, identifier value is randomly assigned by
                    # create_an_imms_obj, so update the expected response dict accordingly
                    expected_response["patient"]["reference"] = hit_imm["patient"]["reference"]
                    expected_response["identifier"][0]["value"] = hit_imm["identifier"][0]["value"]
                    self.assertEqual(hit_imm, expected_response)

    @staticmethod
    def filter_my_imms_from_search_result(search_body: dict, *my_ids) -> List[dict]:
        return [entry["resource"] for entry in search_body["entry"] if entry["resource"]["id"] in my_ids]
