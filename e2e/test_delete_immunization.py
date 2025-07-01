from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import generate_imms_resource
import unittest


@unittest.skip("This test is skipped because it requires a live FHIR server connection.")
class TestDeleteImmunization(ImmunizationBaseTest):

    def test_delete_imms(self):
        """it should delete a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                immunization_data_list = [
                    generate_imms_resource(),
                    generate_imms_resource(sample_data_file_name="completed_rsv_immunization_event")
                ]

                created_ids = []
                for imms_data in immunization_data_list:
                    response = imms_api.create_immunization(imms_data)
                    self.assertEqual(response.status_code, 201)
                    created_id = parse_location(response.headers["Location"])
                    created_ids.append(created_id)

                # When
                for imms_id in created_ids:
                    delete_response = imms_api.delete_immunization(imms_id)

                    # Then
                    self.assertEqual(delete_response.status_code, 204)
                    self.assertEqual(delete_response.text, "")
                    self.assertTrue("Location" not in delete_response.headers)

    def test_delete_immunization_already_deleted(self):
        """it should return 404 when deleting a deleted resource"""
        imms = self.default_imms_api.create_a_deleted_immunization_resource()
        response = self.default_imms_api.delete_immunization(imms["id"], expected_status_code=404)
        self.assert_operation_outcome(response, 404)
