from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import create_an_imms_obj


class TestGetImmunization(ImmunizationBaseTest):
    def test_get_imms(self):
        """it should get a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                imms = create_an_imms_obj()
                response = imms_api.create_immunization(imms)
                assert response.status_code == 201, response.text
                imms_id = parse_location(response.headers["Location"])

                # When
                response = imms_api.get_immunization_by_id(imms_id)

                # Then
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["id"], imms_id)

    def not_found(self):
        """it should return 404 if resource doesn't exist"""
        response = self.default_imms_api.get_immunization_by_id("some-id-that-does-not-exist")
        self.assert_operation_outcome(response, 404)

    def malformed_id(self):
        """it should return 400 if resource id is invalid"""
        response = self.default_imms_api.get_immunization_by_id("some_id_that_is_malformed")
        self.assert_operation_outcome(response, 400)

    def get_deleted_imms(self):
        """it should return 404 if resource has been deleted"""
        imms = self.create_a_deleted_immunization_resource(self.default_imms_api)
        response = self.default_imms_api.get_immunization_by_id(imms["id"])
        self.assert_operation_outcome(response, 404)
