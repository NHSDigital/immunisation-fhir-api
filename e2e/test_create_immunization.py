import uuid
from decimal import Decimal
from utils.base_test import ImmunizationBaseTest
from utils.resource import create_an_imms_obj, get_full_row_from_identifier


class TestCreateImmunization(ImmunizationBaseTest):
    def test_create_imms(self):
        """it should create a FHIR Immunization resource"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given
                imms = create_an_imms_obj()
                del imms["id"]

                # When
                response = imms_api.create_immunization(imms)

                # Then
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.text, "")
                self.assertTrue("Location" in response.headers)

    def test_non_unique_identifier(self):
        """it should give 422 if the identifier is not unique"""
        imms = create_an_imms_obj()
        del imms["id"]
        _ = self.create_immunization_resource(self.default_imms_api, imms)
        new_id = str(uuid.uuid4())
        imms["id"] = new_id
        del imms["id"]

        # When update the same object (it has the same identifier)
        response = self.default_imms_api.create_immunization(imms)
        # Then
        self.assert_operation_outcome(response, 422)

    def test_bad_nhs_number(self):
        """it should reject the request if nhs-number does not exist"""
        bad_nhs_number = "7463384756"
        imms = create_an_imms_obj(nhs_number=bad_nhs_number)
        del imms["id"]

        response = self.default_imms_api.create_immunization(imms)

        self.assert_operation_outcome(response, 400, bad_nhs_number)

    def test_bad_dose_quantity_value(self):
        """it should reject the request if doseQuantity.value is more than 4 decimal places"""

        imms = create_an_imms_obj()
        imms["doseQuantity"]["value"] = Decimal("0.12345")

        response = self.default_imms_api.create_immunization(imms)

        self.assert_operation_outcome(
            response, 400, "doseQuantity.value must be a number with a maximum of 4 decimal places"
        )

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

    def test_no_nhs_number(self):
        """it should accept the request if nhs-number is missing"""
        imms = create_an_imms_obj()
        del imms["contained"][1]["identifier"][0]["value"]
        del imms["id"]

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
        imms = create_an_imms_obj()
        del imms["id"]
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
        imms = create_an_imms_obj(
            nhs_number=None, sample_data_file_name="completed_covid19_immunization_event_with_id_mandatory_fields_only"
        )
        del imms["id"]

        # When
        response = self.default_imms_api.create_immunization(imms)

        # Then
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.text, "")
        self.assertTrue("Location" in response.headers)

    def test_create_imms_with_missing_mandatory_field(self):
        """Test that data  is rejected for create if one of the mandatory fields is missing"""
        imms = create_an_imms_obj(
            nhs_number=None, sample_data_file_name="completed_covid19_immunization_event_with_id_mandatory_fields_only"
        )
        del imms["id"]
        del imms["primarySource"]

        # When
        response = self.default_imms_api.create_immunization(imms)

        # Then
        self.assert_operation_outcome(response, 400, "primarySource is a mandatory field")
