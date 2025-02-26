import time
from decimal import Decimal

from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import generate_imms_resource, generate_filtered_imms_resource
from utils.mappings import EndpointOperationNames, VaccineTypes


class TestGetImmunization(ImmunizationBaseTest):

    def test_get_imms(self):
        """it should get a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                immunizations = [
                    {
                        "data": generate_imms_resource(),
                        "expected": generate_filtered_imms_resource(
                            crud_operation_to_filter_for=EndpointOperationNames.READ)
                    },
                    {
                        "data": generate_imms_resource(sample_data_file_name="completed_rsv_immunization_event"),
                        "expected": generate_filtered_imms_resource(
                            crud_operation_to_filter_for=EndpointOperationNames.READ,
                            vaccine_type=VaccineTypes.rsv
                        )
                    }
                ]

                # Create immunizations and capture IDs
                for immunization in immunizations:
                    response = imms_api.create_immunization(immunization["data"])
                    self.assertEqual(response.status_code, 201)

                    immunization_id = parse_location(response.headers["Location"])
                    immunization["id"] = immunization_id
                    immunization["expected"]["id"] = immunization_id

                # When - Retrieve and validate each immunization by ID
                for immunization in immunizations:
                    response = imms_api.get_immunization_by_id(immunization["id"])

                    # Then
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["id"], immunization["id"])
                    self.assertEqual(response.json(parse_float=Decimal), immunization["expected"])
                    time.sleep(20)

    def not_found(self):
        """it should return 404 if resource doesn't exist"""
        response = self.default_imms_api.get_immunization_by_id("some-id-that-does-not-exist")
        self.assert_operation_outcome(response, 404)
        time.sleep(20)

    def malformed_id(self):
        """it should return 400 if resource id is invalid"""
        response = self.default_imms_api.get_immunization_by_id("some_id_that_is_malformed")
        self.assert_operation_outcome(response, 400)
        time.sleep(20)

    def get_deleted_imms(self):
        """it should return 404 if resource has been deleted"""
        imms = self.create_a_deleted_immunization_resource(self.default_imms_api)
        response = self.default_imms_api.get_immunization_by_id(imms["id"])
        self.assert_operation_outcome(response, 404)
        time.sleep(20)

    def test_get_imms_with_tbc_pk(self):
        """it should get a FHIR Immunization resource if the nhs number is TBC"""
        imms = generate_imms_resource()
        del imms["contained"][1]["identifier"][0]["value"]
        imms_id = self.create_immunization_resource(self.default_imms_api, imms)

        response = self.default_imms_api.get_immunization_by_id(imms_id)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], imms_id)
        time.sleep(20)
