import uuid
from utils.base_test import ImmunizationBaseTest
from utils.resource import create_an_imms_obj


class TestCreateImmunization(ImmunizationBaseTest):
    def test_create_imms(self):
        """it should create a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                imms = create_an_imms_obj()

                # When
                response = imms_api.create_immunization(imms)

                # Then
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.text, "")
                self.assertTrue("Location" in response.headers)

    def test_non_unique_identifier(self):
        """it should give 422 if the identifier is not unique"""
        imms = create_an_imms_obj()
        _ = self.create_immunization_resource(self.default_imms_api, imms)
        new_id = str(uuid.uuid4())
        imms["id"] = new_id

        # When update the same object (it has the same identifier)
        response = self.default_imms_api.create_immunization(imms)
        # Then
        self.assert_operation_outcome(response, 422)

    def test_bad_nhs_number(self):
        """it should reject the request if nhs-number does not exist"""
        bad_nhs_number = "7463384756"
        imms = create_an_imms_obj(nhs_number=bad_nhs_number)

        response = self.default_imms_api.create_immunization(imms)

        self.assert_operation_outcome(response, 400, bad_nhs_number)

    def test_validation(self):
        """it should validate Immunization"""
        # NOTE: This e2e test is here to prove validation logic is wired to the backend.
        #  validation is thoroughly unit tested in the backend code
        imms = create_an_imms_obj()
        invalid_datetime = "2020-12-14"
        imms["occurrenceDateTime"] = invalid_datetime

        # When
        response = self.default_imms_api.create_immunization(imms)

        # Then
        self.assert_operation_outcome(response, 400, "occurrenceDateTime")
