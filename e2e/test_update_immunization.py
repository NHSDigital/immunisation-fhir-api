import copy
import uuid

from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import create_an_imms_obj


class TestUpdateImmunization(ImmunizationBaseTest):

    def test_update_imms(self):
        """it should update a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                imms = create_an_imms_obj()
                response = imms_api.create_immunization(imms)
                assert response.status_code == 201
                imms_id = parse_location(response.headers["Location"])

                # When
                update_payload = copy.deepcopy(imms)
                update_payload["id"] = imms_id
                update_payload["status"] = "not-done"
                response = self.app_res_imms_api.update_immunization(imms_id, update_payload)

                # Then
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.text, "")
                self.assertTrue("Location" not in response.headers)

    def test_update_none_existing_record(self):
        """update should create a new Immunization if id doesn't exist"""
        imms_id = str(uuid.uuid4())
        imms = create_an_imms_obj(imms_id)

        response = self.app_res_imms_api.update_immunization(imms_id, imms)

        self.assertEqual(response.status_code, 201, response.text)

    def test_update_inconsistent_id(self):
        """update should fail if id in the path doesn't match with the id in the message"""
        msg_id = str(uuid.uuid4())
        imms = create_an_imms_obj(msg_id)
        path_id = str(uuid.uuid4())

        response = self.app_res_imms_api.update_immunization(path_id, imms)

        self.assert_operation_outcome(response, 400, contains=path_id)

    def test_update_deleted_imms(self):
        """updating deleted record will undo the delete"""
        # This behaviour is consistent. Getting a deleted record will result in a 404.
        #  An update of a non-existent record should result in creating a new record
        #  Therefore, the new resource's id must be different from the original one

        imms = self.create_a_deleted_immunization_resource(self.app_res_imms_api)
        deleted_id = imms["id"]

        response = self.app_res_imms_api.update_immunization(deleted_id, imms)

        self.assertEqual(response.status_code, 201, response.text)
        new_imms_id = parse_location(response.headers["Location"])
        self.assertNotEqual(deleted_id, new_imms_id)