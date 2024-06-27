"""Test immunization pre validation rules on the model"""

import unittest
from copy import deepcopy
from jsonpath_ng.ext import parse
from pydantic import ValidationError


from src.mappings import VaccineTypes, Mandation
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

    def test_collected_errors(self):
        """Test that when passed multiple validation errors, it returns a list of all expected errors."""
        # TODO: BUG Fix this test so that it collects post-validation errors (the ones here are pre-validation)

        covid_19_json_data = deepcopy(self.completed_json_data[VaccineTypes.covid_19])

        # remove name[0].given for 'Patient'
        for item in covid_19_json_data.get("contained", []):
            if item.get("resourceType") == "Patient":
                if "name" in item and item["name"] and "given" in item["name"][0]:
                    item["name"][0]["given"] = None

        # remove actor.identifier.value for 'Organization'
        for performer in covid_19_json_data.get("performer", []):
            if performer.get("actor", {}).get("type") == "Organization":
                if "identifier" in performer["actor"]:
                    performer["actor"]["identifier"]["value"] = None
                if "display" in performer["actor"]:
                    performer["actor"]["display"] = None

        # remove postalCode for 'Patient'
        for item in covid_19_json_data.get("contained", []):
            if item.get("resourceType") == "Patient":
                if "address" in item and item["address"]:
                    item["address"][0]["postalCode"] = None

        # remove 'given' for 'Practitioner'
        for item in covid_19_json_data.get("contained", []):
            if item.get("resourceType") == "Practitioner":
                if "name" in item and item["name"] and "given" in item["name"][0]:
                    item["name"][0]["given"] = None

        # remove 'primarySource'
        covid_19_json_data["primarySource"] = None

        expected_errors = [
            "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given must be an array",
            "performer[?(@.actor.type=='Organization')].actor.identifier.value must be a string",
            "performer[?@.actor.type == 'Organization'].actor.display must be a string",
            "contained[?(@.resourceType=='Patient')].address[0].postalCode must be a string",
            "contained[?(@.resourceType=='Practitioner')].name[0].given must be an array",
            "primarySource must be a boolean",
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
            self.assertTrue(self.validator.validate(json_data))

    def test_post_validate_and_set_vaccine_type(self):
        """
        Test validate_and_set_validate_and_set_vaccine_type accepts valid values, rejects invalid
        values and rejects missing data
        """
        field_location = "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code"

        # Test that a valid combination of disease codes is accepted and vaccine_type is set correctly
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            self.assertTrue(self.validator.validate(self.completed_json_data[vaccine_type]))
            self.assertEqual(vaccine_type, self.validator.post_validators.vaccine_type)

        # Test that an invalid single disease code is rejected
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.completed_json_data[VaccineTypes.covid_19]),
            field_location=field_location,
            invalid_value="INVALID_VALUE",
            expected_error_message="['INVALID_VALUE'] is not a valid combination of disease codes for this service",
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
            expected_error_message="['14189004', 'INVALID', '36653000'] is not a valid combination"
            + " of disease codes for this service",
        )

        # Test that json data which doesn't contain a targetDisease code is rejected
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

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
        # covid_19_json_data = deepcopy(self.completed_json_data[VaccineTypes.covid_19])

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

    def test_post_organization_display(self):
        """Test that the JSON data is accepted if it does not contain organization_display"""
        MandationTests.test_missing_field_accepted(self, "performer[?(@.actor.type=='Organization')].actor.display")

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

    def test_post_practitioner_identifier_value(self):
        """Test that the JSON data is accepted if it does not contain practitioner_identifier_value"""
        MandationTests.test_missing_field_accepted(
            self, "contained[?(@.resourceType=='Practitioner')].identifier[0].value"
        )

    def test_post_practitioner_identifier_system(self):
        """
        Test that present or absent pratitioner_identifier_system is accepted or rejected
        as appropriate dependent on other fields
        """
        practitioner_identifier_value_field_location = (
            "contained[?(@.resourceType=='Practitioner')].identifier[0].value"
        )

        practitioner_identifier_system_field_location = (
            "contained[?(@.resourceType=='Practitioner')].identifier[0].system"
        )

        # Test COVID-19 and FLU cases
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_mandation_for_interdependent_fields(
                self,
                dependent_field_location=practitioner_identifier_system_field_location,
                dependent_on_field_location=practitioner_identifier_value_field_location,
                vaccine_type=vaccine_type,
                mandation_when_dependent_on_field_present=Mandation.mandatory,
                mandation_when_dependent_on_field_absent=Mandation.optional,
                expected_error_message=f"{practitioner_identifier_system_field_location} is "
                + f"mandatory when {practitioner_identifier_value_field_location} is present and "
                + f"vaccination type is {vaccine_type}",
                valid_json_data=deepcopy(self.completed_json_data[vaccine_type]),
            )

        # Test HPV and MMR cases
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_interdependent_fields(
                self,
                dependent_field_location=practitioner_identifier_system_field_location,
                dependent_on_field_location=practitioner_identifier_value_field_location,
                vaccine_type=vaccine_type,
                mandation_when_dependent_on_field_present=Mandation.optional,
                mandation_when_dependent_on_field_absent=Mandation.optional,
                valid_json_data=deepcopy(self.completed_json_data[vaccine_type]),
            )

    def test_post_recorded(self):
        """Test that the JSON data is rejected if it does not contain recorded"""
        MandationTests.test_missing_mandatory_field_rejected(self, "recorded")

    def test_post_primary_source(self):
        """Test that the JSON data is rejected if it does not contain primary_source"""
        MandationTests.test_missing_mandatory_field_rejected(self, "primarySource")

    def test_post_report_origin_text(self):
        """
        Test that present or absent report_origin_text is accepted or rejected
        as appropriate dependent on other fields
        """
        valid_json_data = deepcopy(self.completed_json_data[VaccineTypes.covid_19])
        field_location = "reportOrigin.text"

        # Test no errors are raised when primarySource is True
        json_data_with_primary_source_true = parse("primarySource").update(deepcopy(valid_json_data), True)
        MandationTests.test_present_field_accepted(self, json_data_with_primary_source_true)
        MandationTests.test_missing_field_accepted(self, field_location, json_data_with_primary_source_true)

        # Test field is present when primarySource is False
        json_data_with_primary_source_false = parse("primarySource").update(deepcopy(valid_json_data), False)
        MandationTests.test_present_field_accepted(self, json_data_with_primary_source_false)
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location,
            json_data_with_primary_source_false,
            expected_error_message=f"{field_location} is mandatory when primarySource is false",
            expected_error_type="MandatoryError",
        )

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
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:

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

        # Test cases for COVID19 and FLU:
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            valid_json_data = deepcopy(self.completed_json_data[vaccine_type])

            # dose_number_positive_int exists, dose_number_string does not exist
            MandationTests.test_present_field_accepted(self, valid_json_data)

            # COVID19: dose_number_positive_int does not exist, dose_number_string exists
            valid_json_data["protocolApplied"][0]["doseNumberString"] = "Dose sequence not recorded"
            MandationTests.test_missing_mandatory_field_rejected(
                self,
                field_location=dose_number_positive_int_field_location,
                valid_json_data=valid_json_data,
                expected_error_message=f"{dose_number_positive_int_field_location} is a mandatory field",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            valid_json_data = deepcopy(self.completed_json_data[vaccine_type])

            # dose_number_positive_int exists, dose_number_string does not exist
            MandationTests.test_present_field_accepted(self, valid_json_data)

            # dose_number_positive_int does not exist, dose_number_string exists
            valid_json_data["protocolApplied"][0]["doseNumberString"] = "Dose sequence not recorded"
            MandationTests.test_missing_field_accepted(self, dose_number_positive_int_field_location, valid_json_data)

    def test_post_vaccine_code_coding_code(self):
        """Test that the JSON data is rejected when vaccine_code_coding_code is absent"""
        field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code"
        MandationTests.test_missing_mandatory_field_rejected(self, field_location, expected_error_type="MandatoryError")

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

        # Test cases for COVID-19
        MandationTests.test_missing_mandatory_field_rejected(self, field_location, expected_error_type="MandatoryError")

        # Test cases for FLU, HPV and MMR
        for vaccine_type in [VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_lot_number(self):
        """Test that present or absent lot_number is accepted or rejected as appropriate dependent on other fields"""
        field_location = "lotNumber"

        # Test cases for COVID-19
        MandationTests.test_missing_mandatory_field_rejected(self, field_location, expected_error_type="MandatoryError")

        # Test cases for FLU, HPV and MMR
        for vaccine_type in [VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_expiration_date(self):
        """
        Test that present or absent expiration_date is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "expirationDate"

        # Test cases for COVID-19
        MandationTests.test_missing_mandatory_field_rejected(self, field_location, expected_error_type="MandatoryError")

        # Test cases for FLU, HPV and MMR
        for vaccine_type in [VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
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

        # Test cases for COVID-19 and FLU
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_missing_mandatory_field_rejected(
                self,
                field_location,
                valid_json_data=self.completed_json_data[vaccine_type],
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_route_coding_display(self):
        """Test that the JSON data is accepted when route_coding_display is absent"""
        MandationTests.test_missing_field_accepted(self, "route.coding[?(@.system=='http://snomed.info/sct')].display")

    def test_post_dose_quantity_value(self):
        """
        Test that present or absent dose_quantity_value is accepted or rejected as appropriate dependent on other fields
        """
        field_location = "doseQuantity.value"

        # Test cases for COVID-19 and FLU
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_missing_mandatory_field_rejected(
                self,
                field_location,
                valid_json_data=self.completed_json_data[vaccine_type],
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_dose_quantity_code(self):
        """
        Test that present or absent dose_quantity_code is accepted or rejected as appropriate dependent on other fields
        """
        field_location = "doseQuantity.code"

        # Test cases for COVID-19 and FLU
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_missing_mandatory_field_rejected(
                self,
                field_location,
                valid_json_data=self.completed_json_data[vaccine_type],
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_missing_field_accepted(self, field_location, self.completed_json_data[vaccine_type])

    def test_post_dose_quantity_unit(self):
        """Test that the JSON data is accepted when dose_quantity_unit is absent"""
        MandationTests.test_missing_field_accepted(self, "doseQuantity.unit")

    def test_post_reason_code_coding_code(self):
        """Test that the JSON data is accepted when reason_code_coding_code is absent"""
        for index in range(len(self.completed_json_data[VaccineTypes.covid_19]["reasonCode"])):
            MandationTests.test_missing_field_accepted(self, f"reasonCode[{index}].coding[0].code")

    def test_post_reason_code_coding_display(self):
        """Test that the JSON data is accepted when reason_code_coding_display is absent"""
        for index in range(len(self.completed_json_data[VaccineTypes.covid_19]["reasonCode"])):
            MandationTests.test_missing_field_accepted(self, f"reasonCode[{index}].coding[0].display")

    def test_post_nhs_number_verification_status_code(self):
        """Test that the JSON data is accepted when nhs_number_verification_status_code is absent"""
        field_location = (
            "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]"
            + ".extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerification"
            + "Status')].valueCodeableConcept.coding[?(@.system=='https://fhir.hl7.org.uk/CodeSystem/"
            + "UKCore-NHSNumberVerificationStatusEngland')].code"
        )
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_nhs_number_verification_status_display(self):
        """Test that the JSON data is accepted when nhs_number_verification_status_display is absent"""
        field_location = (
            "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]"
            + ".extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerification"
            + "Status')].valueCodeableConcept.coding[?(@.system=='https://fhir.hl7.org.uk/CodeSystem/"
            + "UKCore-NHSNumberVerificationStatusEngland')].display"
        )

        MandationTests.test_missing_field_accepted(self, field_location)

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

    def test_post_reduce_validation_code(self):
        """Test that present or absent reduce_validation_code is accepted"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='ReduceValidationCode')].answer[0].valueString"
        )
        MandationTests.test_missing_field_accepted(self, field_location)
        MandationTests.test_present_field_accepted(
            self, valid_json_data=deepcopy(self.completed_json_data[VaccineTypes.covid_19])
        )
