import uuid

from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, valid_nhs_number2, mmr_code, flu_code
from utils.resource import create_an_imms_obj


class TestSearchImmunization(ImmunizationBaseTest):
    # NOTE: In each test, the result may contain more hits. We only assert if the resource that we created is
    #  in the result set and assert the one that we don't expect is not present.
    #  This is to make these tests stateless otherwise; we need to clean up the db after each test

    def store_records(self, *resources):
        for res in resources:
            imms_id = self.create_immunization_resource(self.default_imms_api, res)
            res["id"] = imms_id

    def test_search_imms(self):
        """it should search records given nhs-number and disease-code"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given two patients each with one mmr
                mmr_p1 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, mmr_code)
                mmr_p2 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number2, flu_code)
                self.store_records(mmr_p1, mmr_p2)

                # When
                response = imms_api.search_immunizations(valid_nhs_number1, "MMR")

                # Then
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["resourceType"], "Bundle")

                resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
                self.assertTrue(mmr_p1["id"] in resource_ids)
                self.assertTrue(mmr_p2["id"] not in resource_ids)

    def test_search_patient_multiple_diseases(self):
        # Given patient has two vaccines
        mmr = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, mmr_code)
        flu = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, flu_code)
        self.store_records(mmr, flu)

        # When
        response = self.default_imms_api.search_immunizations(valid_nhs_number1, "MMR")

        # Then
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
        self.assertTrue(mmr["id"] in resource_ids)
        self.assertTrue(flu["id"] not in resource_ids)

    def test_search_ignore_deleted(self):
        # Given patient has three vaccines and the last one is deleted
        mmr1 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, mmr_code)
        mmr2 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, mmr_code)
        self.store_records(mmr1, mmr2)

        to_delete_mmr = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, mmr_code)
        deleted_mmr = self.create_a_deleted_immunization_resource(self.default_imms_api, to_delete_mmr)

        # When
        response = self.default_imms_api.search_immunizations(valid_nhs_number1, "MMR")

        # Then
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
        self.assertTrue(mmr1["id"] in resource_ids)
        self.assertTrue(mmr2["id"] in resource_ids)
        self.assertTrue(deleted_mmr["id"] not in resource_ids)
