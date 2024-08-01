from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import create_an_imms_obj


class TestDeleteImmunization(ImmunizationBaseTest):

    def test_delete_imms(self):
        """it should delete a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                imms = create_an_imms_obj()
                del imms["id"]
                response = imms_api.create_immunization(imms)
                assert response.status_code == 201, response.text
                imms_id = parse_location(response.headers["Location"])

                # When
                response = imms_api.delete_immunization(imms_id)

                # Then
                self.assertEqual(response.status_code, 204, response.text)
                self.assertEqual(response.text, "")
                self.assertTrue("Location" not in response.headers)

    def test_delete_immunization_already_deleted(self):
        """it should return 404 when deleting a deleted resource"""
        imms = self.create_a_deleted_immunization_resource(self.default_imms_api)
        response = self.default_imms_api.delete_immunization(imms["id"])
        self.assert_operation_outcome(response, 404)
