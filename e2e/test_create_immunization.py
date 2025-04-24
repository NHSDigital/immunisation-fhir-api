from utils.base_test import ImmunizationBaseTest
from utils.resource import generate_imms_resource, get_full_row_from_identifier


class TestCreateImmunization(ImmunizationBaseTest):

    def test_create_imms(self):
        """it should create a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                immunizations = [
                    generate_imms_resource(),
                    generate_imms_resource(
                        sample_data_file_name="completed_rsv_immunization_event"
                    ),
                ]

                for immunization in immunizations:
                    # When
                    response = imms_api.create_immunization(immunization)

                    # Then
                    self.assertEqual(response.status_code, 201, response.text)
                    self.assertEqual(response.text, "")
                    self.assertIn("Location", response.headers)

    def test_non_unique_identifier(self):
        """
        it should give 422 if the identifier is not unique, even if the original imms event has been deleted and/ or
        reinstated
        """
        # Set up
        imms = generate_imms_resource()
        imms_id = self.default_imms_api.create_immunization_resource(imms)
        self.assertEqual(
            self.default_imms_api.get_immunization_by_id(imms_id).status_code, 200
        )

        # Check that duplicate CREATE request is rejected
        self.assert_operation_outcome(
            self.default_imms_api.create_immunization(imms, expected_status_code=422),
            422,
        )

        # Check that duplice CREATE request is rejected after the event is updated
        imms["id"] = imms_id  # Imms fhir resource should include the id for update
        self.default_imms_api.update_immunization(imms_id, imms)
        self.assertEqual(
            self.default_imms_api.get_immunization_by_id(imms_id).status_code, 200
        )
        del imms["id"]  # Imms fhir resource should not include an id for create
        self.assert_operation_outcome(
            self.default_imms_api.create_immunization(imms, expected_status_code=422),
            422,
        )

        # Check that duplice CREATE request is rejected after the event is updated then deleted
        self.default_imms_api.delete_immunization(imms_id)
        self.assertEqual(
            self.default_imms_api.get_immunization_by_id(
                imms_id, expected_status_code=404
            ).status_code,
            404,
        )
        self.assert_operation_outcome(
            self.default_imms_api.create_immunization(imms, expected_status_code=422),
            422,
        )

        # Check that duplice CREATE request is rejected after the event is updated then deleted then reinstated
        imms["id"] = imms_id  # Imms fhir resource should include the id for update
        self.default_imms_api.update_immunization(imms_id, imms)
        self.assertEqual(
            self.default_imms_api.get_immunization_by_id(imms_id).status_code, 200
        )
        del imms["id"]  # Imms fhir resource should not include an id for create
        self.assert_operation_outcome(
            self.default_imms_api.create_immunization(imms, expected_status_code=422),
            422,
        )

    def test_bad_nhs_number(self):
        """it should reject the request if nhs-number does not exist"""
        bad_nhs_number = "7463384756"
        imms = generate_imms_resource(nhs_number=bad_nhs_number)

        response = self.default_imms_api.create_immunization(
            imms, expected_status_code=400
        )

        self.assert_operation_outcome(response, 400, bad_nhs_number)

    def test_validation(self):
        """it should validate Immunization"""
        # NOTE: This e2e test is here to prove validation logic is wired to the backend.
        #  validation is thoroughly unit tested in the backend code
        imms = generate_imms_resource()
        invalid_datetime = "2020-12-32"
        imms["occurrenceDateTime"] = invalid_datetime
        # When
        response = self.default_imms_api.create_immunization(
            imms, expected_status_code=400
        )

        # Then
        self.assert_operation_outcome(response, 400, "occurrenceDateTime")

    def test_no_nhs_number(self):
        """it should accept the request if nhs-number is missing"""
        imms = generate_imms_resource()
        del imms["contained"][1]["identifier"][0]["value"]

        response = self.default_imms_api.create_immunization(imms)

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.text, "")
        self.assertTrue("Location" in response.headers)

        # Check that nhs_number has been stored in IEDS as TBC
        identifier = response.headers.get("location").split("/")[-1]
        patient_pk = get_full_row_from_identifier(identifier).get("PatientPK")
        self.assertEqual(patient_pk, "Patient#TBC")

    def test_no_patient_identifier(self):
        """it should accept the request if patient identifier is missing"""
        imms = generate_imms_resource()
        del imms["contained"][1]["identifier"]

        response = self.default_imms_api.create_immunization(imms)

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.text, "")
        self.assertTrue("Location" in response.headers)

        # Check that nhs_number has been stored in IEDS as TBC
        identifier = response.headers.get("location").split("/")[-1]
        patient_pk = get_full_row_from_identifier(identifier).get("PatientPK")
        self.assertEqual(patient_pk, "Patient#TBC")

    def test_create_imms_for_mandatory_fields_only(self):
        """Test that data containing only the mandatory fields is accepted for create"""
        imms = generate_imms_resource(
            nhs_number=None,
            sample_data_file_name="completed_covid19_immunization_event_mandatory_fields_only",
        )

        # When
        response = self.default_imms_api.create_immunization(imms)

        # Then
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.text, "")
        self.assertTrue("Location" in response.headers)

    def test_create_imms_with_missing_mandatory_field(self):
        """Test that data  is rejected for create if one of the mandatory fields is missing"""
        imms = generate_imms_resource(
            nhs_number=None,
            sample_data_file_name="completed_covid19_immunization_event_mandatory_fields_only",
        )
        del imms["primarySource"]

        # When
        response = self.default_imms_api.create_immunization(
            imms, expected_status_code=400
        )

        # Then
        self.assert_operation_outcome(
            response, 400, "primarySource is a mandatory field"
        )
