"""Test immunization pre validation rules on the model"""

import unittest
from copy import deepcopy
from pydantic import ValidationError
from fhir.resources.R4B.immunization import Immunization


from src.mappings import VaccineTypes
from src.models.fhir_immunization import ImmunizationValidator
from tests.utils.generic_utils import (
    # these have an underscore to avoid pytest collecting them as tests
    test_invalid_values_rejected as _test_invalid_values_rejected,
    load_json_data,
)
from tests.utils.mandation_test_utils import MandationTests


class TestImmunizationModelPostValidationRules(unittest.TestCase):
    """Test immunization post validation rules on the FHIR model"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.validator = ImmunizationValidator()
        self.completed_json_data = {
            VaccineTypes.covid_19: load_json_data("completed_covid19_immunization_event.json"),
            VaccineTypes.flu: load_json_data("completed_flu_immunization_event.json"),
            VaccineTypes.hpv: load_json_data("completed_hpv_immunization_event.json"),
            VaccineTypes.mmr: load_json_data("completed_mmr_immunization_event.json"),
        }
        self.all_vaccine_types = [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]

    def test_collected_errors(self):
        """Test that when passed multiple validation errors, it returns a list of all expected errors"""

        covid_19_json_data = deepcopy(self.completed_json_data[VaccineTypes.covid_19])

        for patient in covid_19_json_data["contained"]:
            if patient["resourceType"] == "Patient":
                for name in patient["name"]:
                    del name["family"]

        for performer in covid_19_json_data["performer"]:
            if performer["actor"].get("type") == "Organization":
                if performer["actor"]["identifier"].get("system") == "https://fhir.nhs.uk/Id/ods-organization-code":
                    del performer["actor"]["identifier"]["system"]

        expected_errors = [
            "contained[?(@.resourceType=='Patient')].name[0].family is a mandatory field",
            "performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field",
        ]

        # assert ValueError raised
        with self.assertRaises(ValueError) as cm:
            self.validator.validate(covid_19_json_data)

        # extract the error messages from the exception
        actual_errors = str(cm.exception).split("; ")

        # assert length of errors
        assert len(actual_errors) == len(expected_errors)

        # assert the error is in the expected error messages
        for error in actual_errors:
            assert error in expected_errors

    def test_sample_data(self):
        """Test that each piece of valid sample data passes post validation"""
        for json_data in list(self.completed_json_data.values()):
            self.assertIsNone(self.validator.validate(json_data))

    def test_post_validate_and_set_vaccine_type(self):
        """
        Test validate_and_set_validate_and_set_vaccine_type accepts valid values, rejects invalid
        values and rejects missing data
        """
        all_target_disease_codes_field_location = (
            "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code"
        )
        first_target_disease_code_field_location = (
            "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"
        )

        # Test that a valid combination of disease codes is accepted
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            self.assertIsNone(self.validator.validate(self.completed_json_data[vaccine_type]))

        # Test that an invalid single disease code is rejected
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.completed_json_data[VaccineTypes.covid_19]),
            field_location=all_target_disease_codes_field_location,
            invalid_value="INVALID_VALUE",
            expected_error_message=f"{all_target_disease_codes_field_location}"
            + " - ['INVALID_VALUE'] is not a valid combination of disease codes for this service",
        )

        # Test that an invalid combination of disease codes is rejected
        invalid_target_disease = [
            {"coding": [{"system": "http://snomed.info/sct", "code": "14189004", "display": "Measles"}]},
            {"coding": [{"system": "http://snomed.info/sct", "code": "INVALID", "display": "Mumps"}]},
            {"coding": [{"system": "http://snomed.info/sct", "code": "36653000", "display": "Rubella"}]},
        ]

        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.completed_json_data[VaccineTypes.covid_19]),
            field_location="protocolApplied[0].targetDisease",
            invalid_value=invalid_target_disease,
            expected_error_message=f"{all_target_disease_codes_field_location} - "
            + "['14189004', 'INVALID', '36653000'] is not a valid combination"
            + " of disease codes for this service",
        )

        # Test that json data which doesn't contain a targetDisease code is rejected
        MandationTests.test_missing_mandatory_field_rejected(self, first_target_disease_code_field_location)

    def test_post_vaccination_procedure_code(self):
        """Test that the JSON data is rejected if it does not contain vaccination_procedure_code"""
        field_location = (
            "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')]"
            + ".valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code"
        )
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_status(self):
        """Test that when status field is absent it is rejected (by FHIR validator)"""
        # This error is raised by the FHIR validator (status is a mandatory FHIR field)
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location="status",
            expected_error_message="field required",
            expected_error_type="value_error.missing",
            is_mandatory_fhir=True,
        )

    def test_post_patient_identifier_value(self):
        """
        Test that the JSON data is accepted when it does not contain patient_identifier_value
        """
        field_location = "contained[?(@.resourceType=='Patient')].identifier[0].value"
        MandationTests.test_missing_field_accepted(self, field_location)

    def test_post_patient_name_given(self):
        """Test that the JSON data is rejected if it does not contain patient_name_given"""
        field_location = "contained[?(@.resourceType=='Patient')].name[0].given"
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_patient_name_family(self):
        """Test that the JSON data is rejected if it does not contain patient_name_family"""
        field_location = "contained[?(@.resourceType=='Patient')].name[0].family"
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_patient_birth_date(self):
        """Test that the JSON data is rejected if it does not contain patient_birth_date"""
        MandationTests.test_missing_mandatory_field_rejected(self, "contained[?(@.resourceType=='Patient')].birthDate")

    def test_post_patient_gender(self):
        """Test that the JSON data is rejected if it does not contain patient_gender"""
        MandationTests.test_missing_mandatory_field_rejected(self, "contained[?(@.resourceType=='Patient')].gender")

    def test_post_patient_address_postal_code(self):
        """Test that the JSON data is rejected if it does not contain patient_address_postal_code"""
        field_location = "contained[?(@.resourceType=='Patient')].address[0].postalCode"
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_occurrence_date_time(self):
        """Test that the JSON data is rejected if it does not contain occurrence_date_time"""
        # This error is raised by the FHIR validator (occurrenceDateTime is a mandatory FHIR field)
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location="occurrenceDateTime",
            expected_error_message="Expect any of field value from this list "
            + "['occurrenceDateTime', 'occurrenceString'].",
            is_mandatory_fhir=True,
        )

    def test_post_organization_identifier_value(self):
        """Test that the JSON data is rejected if it does not contain organization_identifier_value"""
        MandationTests.test_missing_mandatory_field_rejected(
            self, "performer[?(@.actor.type=='Organization')].actor.identifier.value"
        )

    def test_post_identifer_value(self):
        """Test that the JSON data is rejected if it does not contain identifier_value"""
        MandationTests.test_missing_mandatory_field_rejected(self, "identifier[0].value")

    def test_post_identifer_system(self):
        """Test that the JSON data is rejected if it does not contain identifier_system"""
        MandationTests.test_missing_mandatory_field_rejected(self, "identifier[0].system")

    def test_post_practitioner_name_given(self):
        """Test that the JSON data is accepted if it does not contain practitioner_name_given"""
        MandationTests.test_missing_field_accepted(self, "contained[?(@.resourceType=='Practitioner')].name[0].given")

    def test_post_practitioner_name_family(self):
        """Test that the JSON data is accepted if it does not contain practitioner_name_family"""
        MandationTests.test_missing_field_accepted(self, "contained[?(@.resourceType=='Practitioner')].name[0].family")

    def test_post_recorded(self):
        """Test that the JSON data is rejected if it does not contain recorded"""
        MandationTests.test_missing_mandatory_field_rejected(self, "recorded")

    def test_post_primary_source(self):
        """Test that the JSON data is rejected if it does not contain primary_source"""
        MandationTests.test_missing_mandatory_field_rejected(self, "primarySource")

    def test_post_vaccination_procedure_display(self):
        """Test that the JSON data is accepted if it does not contain vaccination_procedure_display"""
        field_location = (
            "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')]"
            + ".valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display"
        )
        MandationTests.test_missing_field_accepted(self, field_location)

    # TODO: To confirm with imms if dose number string validation is correct (current working assumption is yes)
    def test_post_dose_number_positive_int(self):
        """
        Test that present or absent protocol_appplied_dose_number_positive_int is accepted or
        rejected as appropriate dependent on other fields.

        NOTE: doseNumber is a mandatory FHIR element of protocolApplied. Therefore is doseNumberPositiveInt is not
        given then doseNumberString must be given instead in order to pass the FHIR validator.
        """
        dose_number_positive_int_field_location = "protocolApplied[0].doseNumberPositiveInt"

        # Test cases which fail the FHIR validator
        for vaccine_type in self.all_vaccine_types:
            # dose_number_positive_int exists , dose_number_string exists
            invalid_json_data = deepcopy(self.completed_json_data[vaccine_type])
            invalid_json_data["protocolApplied"][0]["doseNumberString"] = "Dose sequence not recorded"
            with self.assertRaises(ValidationError) as error:
                self.validator.validate(invalid_json_data)
            self.assertTrue(
                (
                    " Any of one field value is expected from this list"
                    + " ['doseNumberPositiveInt', 'doseNumberString'], but got multiple! (type=value_error)"
                )
                in str(error.exception)
            )

            # dose_number_positive_int does not exist, dose_number_string does not exist
            valid_json_data = deepcopy(self.completed_json_data[vaccine_type])
            MandationTests.test_missing_mandatory_field_rejected(
                self,
                field_location=dose_number_positive_int_field_location,
                valid_json_data=valid_json_data,
                expected_error_message="Expect any of field value from this list "
                + "['doseNumberPositiveInt', 'doseNumberString'].",
                is_mandatory_fhir=True,
            )

            # dose_number_positive_int exists, dose_number_string does not exist
            valid_json_data = deepcopy(self.completed_json_data[vaccine_type])
            MandationTests.test_present_field_accepted(self, valid_json_data)

            # dose_number_positive_int does not exist, dose_number_string exists
            valid_json_data["protocolApplied"][0]["doseNumberString"] = "Dose sequence not recorded"
            MandationTests.test_missing_field_accepted(self, dose_number_positive_int_field_location, valid_json_data)

    def test_post_vaccine_code_coding_code(self):
        """Test that the JSON data is rejected when vaccine_code_coding_code is absent"""
        field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code"
        MandationTests.test_missing_field_accepted(self, field_location)

    def test_post_vaccine_code_coding_display(self):
        """Test that the JSON data is accepted when vaccine_code_coding_display is absent"""
        field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display"
        MandationTests.test_missing_field_accepted(self, field_location)

    def test_post_manufacturer_display(self):
        """
        Test that present or absent manufacturer_display is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "manufacturer.display"
        for vaccine_type in self.all_vaccine_types:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_lot_number(self):
        """Test that present or absent lot_number is accepted or rejected as appropriate dependent on other fields"""
        field_location = "lotNumber"
        for vaccine_type in self.all_vaccine_types:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_expiration_date(self):
        """
        Test that present or absent expiration_date is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "expirationDate"
        for vaccine_type in self.all_vaccine_types:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_site_coding_code(self):
        """Test that the JSON data is accepted when site_coding_code is absent"""
        MandationTests.test_missing_field_accepted(self, "site.coding[?(@.system=='http://snomed.info/sct')].code")

    def test_post_site_coding_display(self):
        """Test that the JSON data is accepted when site_coding_display is absent"""
        MandationTests.test_missing_field_accepted(self, "site.coding[?(@.system=='http://snomed.info/sct')].display")

    def test_post_route_coding_code(self):
        """
        Test that present or absent route_coding_code is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "route.coding[?(@.system=='http://snomed.info/sct')].code"
        for vaccine_type in self.all_vaccine_types:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_route_coding_display(self):
        """Test that the JSON data is accepted when route_coding_display is absent"""
        MandationTests.test_missing_field_accepted(self, "route.coding[?(@.system=='http://snomed.info/sct')].display")

    def test_post_dose_quantity_value(self):
        """
        Test that present or absent dose_quantity_value is accepted or rejected as appropriate dependent on other fields
        """
        field_location = "doseQuantity.value"
        for vaccine_type in self.all_vaccine_types:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_dose_quantity_code(self):
        """
        Test that present or absent dose_quantity_code is accepted or rejected as appropriate dependent on other fields
        """
        field_location = "doseQuantity.code"
        for vaccine_type in self.all_vaccine_types:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_dose_quantity_unit(self):
        """Test that the JSON data is accepted when dose_quantity_unit is absent"""
        MandationTests.test_missing_field_accepted(self, "doseQuantity.unit")

    def test_post_reason_code_coding_code(self):
        """Test that the JSON data is accepted when reason_code_coding_code is absent"""
        for index in range(len(self.completed_json_data[VaccineTypes.covid_19]["reasonCode"])):
            MandationTests.test_missing_field_accepted(self, f"reasonCode[{index}].coding[0].code")

    def test_post_organization_identifier_system(self):
        """Test that the JSON data is rejected if it does not contain organization_identifier_system"""
        MandationTests.test_missing_mandatory_field_rejected(
            self, "performer[?(@.actor.type=='Organization')].actor.identifier.system"
        )

    def test_post_location_identifier_value(self):
        """
        Test that the JSON data is rejected if it does and does not contain
        location_identifier_value as appropriate
        """
        field_location = "location.identifier.value"
        # Test cases for COVID-19, FLU, HPV and MMR where it is mandatory
        for vaccine_type in (VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            valid_json_data = deepcopy(self.completed_json_data[vaccine_type])
            MandationTests.test_missing_mandatory_field_rejected(self, field_location, valid_json_data)

    def test_post_location_identifier_system(self):
        """
        Test that the JSON data is rejected if it does and does not contain location_identifier_system as appropriate
        """
        field_location = "location.identifier.system"
        # Test cases for COVID-19, FLU, HPV and MMR where it is mandatory
        for vaccine_type in (VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            valid_json_data = deepcopy(self.completed_json_data[vaccine_type])
            MandationTests.test_missing_mandatory_field_rejected(self, field_location, valid_json_data)

    def test_post_no_snomed_code(self):
        """test that only snomed system is accepted"""
        covid_19_json_data = deepcopy(self.completed_json_data[VaccineTypes.covid_19])
        for protocol in covid_19_json_data.get("protocolApplied", []):
            target_diseases = protocol.get("targetDisease", [])
            for i, _ in enumerate(target_diseases):
                for coding in target_diseases[i].get("coding", []):
                    if i == 0:
                        coding["system"] = "http://othersystem.com/system1"
                    else:
                        coding["system"] = "http://Notsnomed.com/system2"

        field_location = "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"

        expected_error_message = f"{field_location} is a mandatory field"

        with self.assertRaises(ValueError) as cm:
            self.validator.validate(covid_19_json_data)

        actual_error_message = str(cm.exception)
        self.assertIn(expected_error_message, actual_error_message)
