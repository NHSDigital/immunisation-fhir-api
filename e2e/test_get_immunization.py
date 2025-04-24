from decimal import Decimal
import uuid

from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import generate_imms_resource, generate_filtered_imms_resource
from utils.mappings import EndpointOperationNames, VaccineTypes


class TestGetImmunization(ImmunizationBaseTest):

    def test_get_imms(self):
        """it should get a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Create one shared UUID per immunization (covid & rsv)
                covid_uuid = str(uuid.uuid4())
                rsv_uuid = str(uuid.uuid4())
                # Given
                immunizations = [
                    {
                        "data": generate_imms_resource(
                            imms_identifier_value=covid_uuid
                        ),
                        "expected": generate_filtered_imms_resource(
                            crud_operation_to_filter_for=EndpointOperationNames.READ,
                            imms_identifier_value=covid_uuid,
                        ),
                    },
                    {
                        "data": generate_imms_resource(
                            sample_data_file_name="completed_rsv_immunization_event",
                            vaccine_type=VaccineTypes.rsv,
                            imms_identifier_value=rsv_uuid,
                        ),
                        "expected": generate_filtered_imms_resource(
                            crud_operation_to_filter_for=EndpointOperationNames.READ,
                            vaccine_type=VaccineTypes.rsv,
                            imms_identifier_value=rsv_uuid,
                        ),
                    },
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
                    self.assertEqual(
                        response.json(parse_float=Decimal), immunization["expected"]
                    )

    def not_found(self):
        """it should return 404 if resource doesn't exist"""
        response = self.default_imms_api.get_immunization_by_id(
            "some-id-that-does-not-exist", expected_status_code=404
        )
        self.assert_operation_outcome(response, 404)

    def malformed_id(self):
        """it should return 400 if resource id is invalid"""
        response = self.default_imms_api.get_immunization_by_id(
            "some_id_that_is_malformed", expected_status_code=400
        )
        self.assert_operation_outcome(response, 400)

    def get_deleted_imms(self):
        """it should return 404 if resource has been deleted"""
        imms = self.default_imms_api.create_a_deleted_immunization_resource()
        response = self.default_imms_api.get_immunization_by_id(
            imms["id"], expected_status_code=404
        )
        self.assert_operation_outcome(response, 404)

    def test_get_imms_with_tbc_pk(self):
        """it should get a FHIR Immunization resource if the nhs number is TBC"""
        imms = generate_imms_resource()
        del imms["contained"][1]["identifier"][0]["value"]
        imms_id = self.default_imms_api.create_immunization_resource(imms)

        response = self.default_imms_api.get_immunization_by_id(imms_id)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], imms_id)
