import copy
import uuid

from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import generate_imms_resource
from utils.mock_pds import MockPds


class TestUpdateImmunization(ImmunizationBaseTest):

    def setUp(self):
        super().setUp()
        self.mock_pds = MockPds("TUI")

    def test_update_imms(self):
        """it should update a FHIR Immunization resource"""
        with self.mock_pds.mock_pds_url("create", {"Location": "AA"}, "", 200):
            for imms_api in self.imms_apis:
                with self.subTest(imms_api):
                    # Given
                    immunization_resources = [
                        generate_imms_resource(),
                        generate_imms_resource(sample_data_file_name="completed_rsv_immunization_event")
                    ]

                    for imms in immunization_resources:
                        # Create the immunization resource
                        response = imms_api.create_immunization(imms)
                        assert response.status_code == 201
                        imms_id = parse_location(response.headers["Location"])

                        # When
                        update_payload = copy.deepcopy(imms)
                        update_payload["id"] = imms_id
                        update_payload["location"]["identifier"]["value"] = "Y11111"
                        response = imms_api.update_immunization(imms_id, update_payload)

                        # Then
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.text, "")
                        self.assertNotIn("Location", response.headers)

    def test_update_non_existent_identifier(self):
        """update a record should fail if identifier is not present"""
        with self.mock_pds.mock_pds_url("create", {"Location": "AA"}, "", 404):
            imms = generate_imms_resource()
            _ = self.create_immunization_resource(self.default_imms_api, imms)
            # NOTE: there is a difference between id and identifier.
            # 422 is expected when identifier is the same across different ids
            # This is why in this test we create a new id but not touching the identifier
            new_imms_id = str(uuid.uuid4())
            imms["id"] = new_imms_id

            # When update the same object (it has the same identifier)
            response = self.default_imms_api.update_immunization(new_imms_id, imms)
            # Then
            self.assert_operation_outcome(response, 404)

    def test_update_inconsistent_id(self):
        """update should fail if id in the path doesn't match with the id in the message"""
        with self.mock_pds.mock_pds_url("create", {"Location": "AA"}, "", 200):
            msg_id = str(uuid.uuid4())
            imms = generate_imms_resource()
            imms["id"] = msg_id
            path_id = str(uuid.uuid4())
            response = self.default_imms_api.update_immunization(path_id, imms)
            self.assert_operation_outcome(response, 400, contains=path_id)

    # TODO: Uncomment this test if it is needed
    # def test_update_deleted_imms(self):
    #     """updating deleted record will undo the delete"""
    #     # This behaviour is consistent. Getting a deleted record will result in a 404.
    #     #  An update of a non-existent record should result in creating a new record
    #     #  Therefore, the new resource's id must be different from the original one

    #     imms = self.create_a_deleted_immunization_resource(self.default_imms_api)
    #     deleted_id = imms["id"]

    #     response = self.default_imms_api.update_immunization(deleted_id, imms)

    #     self.assertEqual(response.status_code, 201, response.text)
    #     new_imms_id = parse_location(response.headers["Location"])
    #     self.assertNotEqual(deleted_id, new_imms_id)
