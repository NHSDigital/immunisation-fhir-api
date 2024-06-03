from typing import List

from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, valid_nhs_number_with_s_flag
from utils.immunisation_api import ImmunisationApi
from utils.resource import get_questionnaire_items, create_an_imms_obj, get_patient_id, get_vaccine_type


class SFlagBaseTest(ImmunizationBaseTest):
    """parent class with a set of assertion helpers"""

    def create_s_flagged_patient(self, imms_api: ImmunisationApi) -> dict:
        imms = create_an_imms_obj(nhs_number=valid_nhs_number_with_s_flag)
        imms_id = self.create_immunization_resource(imms_api, imms)
        imms["id"] = imms_id
        return imms

    def create_not_s_flagged_patient(self, imms_api: ImmunisationApi) -> dict:
        imms = create_an_imms_obj(nhs_number=valid_nhs_number1)
        imms_id = self.create_immunization_resource(imms_api, imms)
        imms["id"] = imms_id
        return imms

    def assert_is_not_filtered(self, imms):
        imms_items = get_questionnaire_items(imms)

        for key in ["Consent"]:
            self.assertTrue(key in [item["linkId"] for item in imms_items])

        performer_actor_organizations = (
            item
            for item in imms["performer"]
            if item.get("actor", {}).get("type") == "Organization")

        self.assertTrue(all(
            performer.get("actor", {}).get("identifier", {}).get("value") != "N2N9I"
            for performer in imms["performer"]))
        self.assertTrue(all(
            organization.get("actor", {}).get("display") is not None
            for organization in performer_actor_organizations))
        self.assertTrue(all(
            organization.get("actor", {}).get("identifier", {}).get("system")
            != "https://fhir.nhs.uk/Id/ods-organization-code"
            for organization in performer_actor_organizations))

        self.assertTrue("reportOrigin" in imms)
        self.assertTrue("location" in imms)


    def assert_is_filtered(self, imms: dict):
        imms_items = get_questionnaire_items(imms)

        for key in ["Consent"]:
            self.assertTrue(key not in [item["linkId"] for item in imms_items])

        performer_actor_organizations = (
            item
            for item in imms["performer"]
            if item.get("actor", {}).get("type") == "Organization")

        self.assertTrue(all(
            organization.get("actor", {}).get("identifier", {}).get("value") == "N2N9I"
            for organization in performer_actor_organizations))
        self.assertTrue(all(
            organization.get("actor", {}).get("display") is None
            for organization in performer_actor_organizations))
        self.assertTrue(all(
            organization.get("actor", {}).get("identifier", {}).get("system")
            == "https://fhir.nhs.uk/Id/ods-organization-code"
            for organization in performer_actor_organizations))

        self.assertTrue("reportOrigin" not in imms)
        self.assertTrue("location" not in imms)


class TestGetSFlagImmunization(SFlagBaseTest):
    """An s-flagged patient contains sensitive data that must be filtered out by backend before being returned"""

    def test_get_s_flagged_imms(self):
        """it should filter certain fields if patient is s-flagged"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms = self.create_s_flagged_patient(imms_api)
                read_imms = imms_api.get_immunization_by_id(imms["id"])
                self.assert_is_filtered(read_imms.json())

    def test_get_not_s_flagged_imms(self):
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms = self.create_not_s_flagged_patient(imms_api)
                read_imms = imms_api.get_immunization_by_id(imms["id"])
                self.assert_is_not_filtered(read_imms.json())

class TestSearchSFlagImmunization(SFlagBaseTest):
    """An s-flagged patient contains sensitive data that must be filtered out by backend before being returned"""

    def test_search_s_flagged_imms(self):
        """it should perform filtering for all search results"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms1 = self.create_s_flagged_patient(imms_api)
                imms2 = self.create_s_flagged_patient(imms_api)
                patient_id = get_patient_id(imms1)
                vaccine_type = get_vaccine_type(imms1)
                # When
                response = imms_api.search_immunizations(patient_id, vaccine_type)
                # Then
                hit_imms = self.filter_my_imms_from_search_result(response.json(), imms1, imms2)
                self.assert_is_filtered(hit_imms[0])
                self.assert_is_filtered(hit_imms[1])

    def test_search_not_s_flagged_imms(self):
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                imms1 = self.create_not_s_flagged_patient(imms_api)
                imms2 = self.create_not_s_flagged_patient(imms_api)
                patient_id = get_patient_id(imms1)
                vaccine_type = get_vaccine_type(imms1)
                # When
                response = imms_api.search_immunizations(patient_id, vaccine_type)
                # Then
                hit_imms = self.filter_my_imms_from_search_result(response.json(), imms1, imms2)
                self.assert_is_not_filtered(hit_imms[0])
                self.assert_is_not_filtered(hit_imms[1])

    @staticmethod
    def filter_my_imms_from_search_result(search_body: dict, *my_imms) -> List[dict]:
        my_ids = [im["id"] for im in my_imms]
        response_imms = [entry["resource"] for entry in search_body["entry"]]

        return [_imms for _imms in response_imms if _imms["id"] in my_ids]
