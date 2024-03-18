"""Test immunization pre validation rules on the model"""

import unittest
from copy import deepcopy

from jsonpath_ng.ext import parse
from mappings import VaccineTypes, Mandation
from models.fhir_immunization import ImmunizationValidator
from .utils.generic_utils import (
    # these have an underscore to avoid pytest collecting them as tests
    test_valid_values_accepted as _test_valid_values_accepted,
    test_invalid_values_rejected as _test_invalid_values_rejected,
    load_json_data,
)
from .utils.mandation_test_utils import MandationTests


class TestImmunizationModelPostValidationRules(unittest.TestCase):
    """Test immunization post validation rules on the FHIR model"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.covid_json_data = load_json_data("sample_covid_immunization_event.json")
        self.flu_json_data = load_json_data("sample_flu_immunization_event.json")
        self.hpv_json_data = load_json_data("sample_hpv_immunization_event.json")
        self.mmr_json_data = load_json_data("sample_mmr_immunization_event.json")
        self.not_done_json_data = load_json_data("sample_immunization_not_done_event.json")
        self.not_done_covid_json_data = load_json_data("sample_immunization_not_done_covid_event.json")
        self.not_done_mmr_json_data = load_json_data("sample_immunization_not_done_mmr_event.json")
        self.reduce_validation_json_data = load_json_data("sample_immunization_reduce_validation_event.json")
        self.validator = ImmunizationValidator()

    def test_sample_data(self):
        """Test that each piece of valid sample data passes post validation"""
        # TODO: vaccinationProcedure item in not-done data extension to be removed
        # dependent on imms team confirmation (it was added to allow tests to pass)
        # TODO: Also test some sample HPV and MMR data
        json_data_to_test = [
            self.covid_json_data,
            self.flu_json_data,
            self.not_done_json_data,
            self.reduce_validation_json_data,
        ]

        for json_data in json_data_to_test:
            validator = ImmunizationValidator()
            self.assertTrue(validator.validate(json_data))

    def test_post_vaccination_procedure_code(self):
        """
        Test validate_and_set_vaccination_procedure_code accepts valid values, rejects invalid
        values and rejects missing data
        """
        valid_json_data = deepcopy(self.covid_json_data)
        field_location = (
            "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/"
            + "Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=="
            + "'http://snomed.info/sct')].code"
        )

        # Test that a valid COVID19 code is accepted and vaccine_type is therefore set to COVID19
        _test_valid_values_accepted(
            self,
            valid_json_data=valid_json_data,
            field_location=field_location,
            valid_values_to_test=["1324681000000101"],
        )
        self.assertEqual(VaccineTypes.covid_19, self.validator.vaccine_type)

        # Test that an invalid code is rejected
        _test_invalid_values_rejected(
            self,
            valid_json_data=valid_json_data,
            field_location=field_location,
            invalid_value="INVALID_VALUE",
            expected_error_message=f"{field_location}: INVALID_VALUE is not a valid code for this service"
        )

        # Test that json data which doesn't contain vaccination_procedure_code is rejected
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_status(self):
        """
        Test that when status field is absent it is rejected (by FHIR validator) and when it is
        present the status property is set equal to it
        """
        # Test that status property is set to the value of status in the JSON data, where it exists
        for valid_value, json_data_to_use in [
            ("completed", self.covid_json_data),
            ("entered-in-error", self.covid_json_data),
            ("not-done", self.not_done_covid_json_data),
        ]:
            valid_json_data = parse("status").update(deepcopy(json_data_to_use), valid_value)
            self.validator.validate(valid_json_data)
            self.assertEqual(valid_value, self.validator.immunization.status)

        # This error is raised by the FHIR validator (status is a mandatory FHIR field)
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location="status",
            expected_bespoke_error_message="field required",
            expected_error_type="value_error.missing",
            is_mandatory_fhir=True,
        )

    def test_post_patient_identifier_value(self):
        """Test that the JSON data is accepted when it does not contain patient_identifier_value"""
        MandationTests.test_missing_field_accepted(self, "contained[?(@.resourceType=='Patient')].identifier[0].value")

    def test_post_patient_name_given(self):
        """Test that the JSON data is rejected if it does not contain patient_name_given"""
        MandationTests.test_missing_mandatory_field_rejected(
            self, "contained[?(@.resourceType=='Patient')].name[0].given"
        )

    def test_post_patient_name_family(self):
        """Test that the JSON data is rejected if it does not contain patient_name_family"""
        MandationTests.test_missing_mandatory_field_rejected(
            self, "contained[?(@.resourceType=='Patient')].name[0].family"
        )

    def test_post_patient_birth_date(self):
        """Test that the JSON data is rejected if it does not contain patient_birth_date"""
        MandationTests.test_missing_mandatory_field_rejected(self, "contained[?(@.resourceType=='Patient')].birthDate")

    def test_post_patient_gender(self):
        """Test that the JSON data is rejected if it does not contain patient_gender"""
        MandationTests.test_missing_mandatory_field_rejected(self, "contained[?(@.resourceType=='Patient')].gender")

    def test_post_patient_address_postal_code(self):
        """
        Test that the JSON data is rejected if it does not contain patient_address_postal_code
        """
        MandationTests.test_missing_mandatory_field_rejected(
            self, "contained[?(@.resourceType=='Patient')].address[0].postalCode"
        )

    def test_post_occurrence_date_time(self):
        """Test that the JSON data is rejected if it does not contain occurrence_date_time"""
        # This error is raised by the FHIR validator (occurrenceDateTime is a mandatory FHIR field)
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location="occurrenceDateTime",
            expected_bespoke_error_message="Expect any of field value from this list "
            + "['occurrenceDateTime', 'occurrenceString'].",
            is_mandatory_fhir=True,
        )

    def test_post_organization_identifier_value(self):
        """
        Test that the JSON data is rejected if it does not contain organization_identifier_value
        """
        MandationTests.test_missing_mandatory_field_rejected(
            self, "performer[?(@.actor.type=='Organization')].actor.identifier.value"
        )

    def test_post_organization_display(self):
        """Test that the JSON data is rejected if it does not contain organization_display"""
        MandationTests.test_missing_mandatory_field_rejected(
            self, "performer[?(@.actor.type=='Organization')].actor.display"
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

    def test_post_practitioner_identifier_value(self):
        """
        Test that the JSON data is accepted if it does not contain practitioner_identifier_value
        """
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

        # Test COVID-19 cases
        MandationTests.test_mandation_for_interdependent_fields(
            self,
            dependent_field_location=practitioner_identifier_system_field_location,
            dependent_on_field_location=practitioner_identifier_value_field_location,
            vaccine_type=VaccineTypes.covid_19,
            mandation_when_dependent_on_field_present=Mandation.mandatory,
            mandation_when_dependent_on_field_absent=Mandation.optional,
            expected_bespoke_error_message=f"{practitioner_identifier_system_field_location} is "
            + f"mandatory when {practitioner_identifier_value_field_location} is present and "
            + f"vaccination type is {VaccineTypes.covid_19}",
        )

        # Tes FLU cases
        MandationTests.test_mandation_for_interdependent_fields(
            self,
            dependent_field_location=practitioner_identifier_system_field_location,
            dependent_on_field_location=practitioner_identifier_value_field_location,
            vaccine_type=VaccineTypes.flu,
            mandation_when_dependent_on_field_present=Mandation.mandatory,
            mandation_when_dependent_on_field_absent=Mandation.optional,
            expected_bespoke_error_message=f"{practitioner_identifier_system_field_location} is "
            + f"mandatory when {practitioner_identifier_value_field_location} is present and "
            + f"vaccination type is {VaccineTypes.flu}",
            valid_json_data=deepcopy(self.flu_json_data),
        )

        # Test HPV cases
        MandationTests.test_mandation_for_interdependent_fields(
            self,
            dependent_field_location=practitioner_identifier_system_field_location,
            dependent_on_field_location=practitioner_identifier_value_field_location,
            vaccine_type=VaccineTypes.hpv,
            mandation_when_dependent_on_field_present=Mandation.optional,
            mandation_when_dependent_on_field_absent=Mandation.optional,
            valid_json_data=deepcopy(self.hpv_json_data),
        )

        # Test MMR cases
        MandationTests.test_mandation_for_interdependent_fields(
            self,
            dependent_field_location=practitioner_identifier_system_field_location,
            dependent_on_field_location=practitioner_identifier_value_field_location,
            vaccine_type=VaccineTypes.mmr,
            mandation_when_dependent_on_field_present=Mandation.optional,
            mandation_when_dependent_on_field_absent=Mandation.optional,
            valid_json_data=deepcopy(self.mmr_json_data),
        )

    def test_post_perfomer_sds_job_role(self):
        """Test that the JSON data is accepted if it does not contain performer_sds_job_role"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='PerformerSDSJobRole')].answer[0].valueString"
        )
        MandationTests.test_missing_field_accepted(self, field_location)

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

        valid_json_data = deepcopy(self.covid_json_data)
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
            expected_bespoke_error_message=f"{field_location} is mandatory when primarySource" + " is false",
            expected_error_type="MandatoryError",
        )

    def test_post_vaccination_procedure_display(self):
        """
        Test that the JSON data is accepted if it does not contain vaccination_procedure_display
        """
        field_location = (
            "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/"
            + "Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=="
            + "'http://snomed.info/sct')].display"
        )
        MandationTests.test_missing_field_accepted(self, field_location)

    def test_post_vaccination_situation_code(self):
        """
        Test that present or absent vaccination_situation_code is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = (
            "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/"
            + "Extension-UKCore-VaccinationSituation')].valueCodeableConcept.coding[?(@.system=="
            + "'http://snomed.info/sct')].code"
        )

        MandationTests.test_mandation_for_status_dependent_fields(
            self,
            field_location=field_location,
            vaccine_type=VaccineTypes.covid_19,
            mandation_when_status_completed=Mandation.optional,
            mandation_when_status_entered_in_error=Mandation.optional,
            mandation_when_status_not_done=Mandation.mandatory,
            expected_bespoke_error_message=f"{field_location} is mandatory when status is " + "'not-done'",
        )

    def test_post_vaccination_situation_display(self):
        """
        Test that the JSON data is accepted when vaccination_situation_display is present or absent
        """
        field_location = (
            "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/"
            + "Extension-UKCore-VaccinationSituation')].valueCodeableConcept.coding[?(@.system=="
            + "'http://snomed.info/sct')].display"
        )

        MandationTests.test_missing_field_accepted(self, field_location)

    def test_post_status_reason_coding_code(self):
        """
        Test that the JSON data is accepted if it contains status_reason_coding_code
        and rejected if not
        """
        field_location = "statusReason.coding[?(@.system=='http://snomed.info/sct')].code"

        for vaccine_type in [
            VaccineTypes.covid_19,
            VaccineTypes.flu,
            VaccineTypes.hpv,
            VaccineTypes.mmr,
        ]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.optional,
                mandation_when_status_entered_in_error=Mandation.optional,
                mandation_when_status_not_done=Mandation.mandatory,
                expected_bespoke_error_message=f"{field_location} is mandatory when status is " + "'not-done'",
                expected_error_type="MandationError",
            )

    def test_post_status_reason_coding_display(self):
        """
        Test that present or absent status_reason_coding_display is accepted or rejected
        as appropriate dependent on other fields
        """
        MandationTests.test_missing_field_accepted(
            self, "statusReason.coding[?(@.system=='http://snomed.info/sct')].code"
        )

    def test_post_protocol_appplied_dose_number_positive_int(self):
        """
        Test that present or absent protocol_appplied_dose_number_positive_int is accepted or
        rejected as appropriate dependent on other fields
        """

        field_location = "protocolApplied[0].doseNumberPositiveInt"
        # protocol_applied_dose_number_positive_int is FHIR mandatory when protocol_applied is
        # present, therefore to test the NHS validators when
        # protocol_applied_dose_number_positive_int is removed, it is necessary to removed
        # the entirety of protocol_applied
        field_to_remove = "protocolApplied"

        # Test cases for COVID-19
        MandationTests.test_mandation_for_status_dependent_fields(
            self,
            field_location,
            vaccine_type=VaccineTypes.covid_19,
            mandation_when_status_completed=Mandation.mandatory,
            mandation_when_status_entered_in_error=Mandation.mandatory,
            mandation_when_status_not_done=Mandation.mandatory,
            expected_bespoke_error_message=f"{field_location} is mandatory when vaccination "
            + f"type is {VaccineTypes.covid_19}",
            field_to_remove=field_to_remove,
        )

        # Test cases for FLU
        MandationTests.test_mandation_for_status_dependent_fields(
            self,
            field_location,
            vaccine_type=VaccineTypes.flu,
            mandation_when_status_completed=Mandation.mandatory,
            mandation_when_status_entered_in_error=Mandation.mandatory,
            mandation_when_status_not_done=Mandation.required,
            expected_bespoke_error_message=f"{field_location} is mandatory when status is "
            + f"'completed' or 'entered-in-error' and vaccination type is {VaccineTypes.flu}",
            field_to_remove=field_to_remove,
        )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
                field_to_remove=field_to_remove,
            )

    def test_post_vaccine_code_coding_code(self):
        """Test that the JSON data is rejected when vaccine_code_coding_code is absent"""
        field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code"

        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location=field_location,
            expected_error_type="MandatoryError",
        )

        # Test not-done data
        field_location = (
            "vaccineCode.coding[?(@.system==" + "'http://terminology.hl7.org/CodeSystem/v3-NullFlavor')].code"
        )

        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location=field_location,
            valid_json_data=deepcopy(self.not_done_json_data),
        )
        
        # Test that valid values are accepted when status is 'not-done'
        _test_valid_values_accepted(
            self,
            valid_json_data=deepcopy(self.not_done_json_data),
            field_location=field_location,
            valid_values_to_test=["NAVU", "UNC", "UNK", "NA"],
        )

        # Test that an invalid values are rejected when status is 'not-done'
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.not_done_json_data),
            field_location=field_location,
            invalid_value="39114911000001105",
            expected_error_message=f"{field_location} must be one of the following:"
            + " NAVU, UNC, UNK, NA when status is 'not-done'"
        )

    def test_post_vaccine_code_coding_display(self):
        """Test that the JSON data is accepted when vaccine_code_coding_display is absent"""
        MandationTests.test_missing_field_accepted(
            self, "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display"
        )

    def test_post_manufacturer_display(self):
        """
        Test that present or absent manufacturer_display is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "manufacturer.display"

        # Test cases for COVID-19
        MandationTests.test_mandation_for_status_dependent_fields(
            self,
            field_location,
            vaccine_type=VaccineTypes.covid_19,
            mandation_when_status_completed=Mandation.mandatory,
            mandation_when_status_entered_in_error=Mandation.mandatory,
            mandation_when_status_not_done=Mandation.required,
            expected_bespoke_error_message=f"{field_location} is mandatory when status is "
            + f"'completed' or 'entered-in-error' and vaccination type is {VaccineTypes.covid_19}",
            expected_error_type="MandatoryError",
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in [VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

    def test_post_lot_number(self):
        """
        Test that present or absent lot_number is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "lotNumber"

        # Test cases for COVID-19
        MandationTests.test_mandation_for_status_dependent_fields(
            self,
            field_location,
            vaccine_type=VaccineTypes.covid_19,
            mandation_when_status_completed=Mandation.mandatory,
            mandation_when_status_entered_in_error=Mandation.mandatory,
            mandation_when_status_not_done=Mandation.required,
            expected_bespoke_error_message=f"{field_location} is mandatory when status is "
            + f"'completed' or 'entered-in-error' and vaccination type is {VaccineTypes.covid_19}",
            expected_error_type="MandatoryError",
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in [VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

    def test_post_expiration_date(self):
        """
        Test that present or absent expiration_date is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "expirationDate"

        # Test cases for COVID-19
        MandationTests.test_mandation_for_status_dependent_fields(
            self,
            field_location,
            vaccine_type=VaccineTypes.covid_19,
            mandation_when_status_completed=Mandation.mandatory,
            mandation_when_status_entered_in_error=Mandation.mandatory,
            mandation_when_status_not_done=Mandation.required,
            expected_bespoke_error_message=f"{field_location} is mandatory when status is "
            + f"'completed' or 'entered-in-error' and vaccination type is {VaccineTypes.covid_19}",
            expected_error_type="MandatoryError",
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in [VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

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
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.mandatory,
                mandation_when_status_entered_in_error=Mandation.mandatory,
                mandation_when_status_not_done=Mandation.required,
                expected_bespoke_error_message=f"{field_location} is mandatory when status is "
                + f"'completed' or 'entered-in-error' and vaccination type is {vaccine_type}",
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

    def test_post_route_coding_display(self):
        """Test that the JSON data is accepted when route_coding_display is absent"""
        MandationTests.test_missing_field_accepted(self, "route.coding[?(@.system=='http://snomed.info/sct')].display")

    def test_post_dose_quantity_value(self):
        """
        Test that present or absent dose_quantity_value is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "doseQuantity.value"

        # Test cases for COVID-19 and FLU
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.mandatory,
                mandation_when_status_entered_in_error=Mandation.mandatory,
                mandation_when_status_not_done=Mandation.required,
                expected_bespoke_error_message=f"{field_location} is mandatory when status is "
                + f"'completed' or 'entered-in-error' and vaccination type is {vaccine_type}",
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

    def test_post_dose_quantity_code(self):
        """
        Test that present or absent dose_quantity_code is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = "doseQuantity.code"

        # Test cases for COVID-19 and FLU
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.mandatory,
                mandation_when_status_entered_in_error=Mandation.mandatory,
                mandation_when_status_not_done=Mandation.required,
                expected_bespoke_error_message=f"{field_location} is mandatory when status is "
                + f"'completed' or 'entered-in-error' and vaccination type is {vaccine_type}",
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

    def test_post_dose_quantity_unit(self):
        """Test that the JSON data is accepted when dose_quantity_unit is absent"""
        MandationTests.test_missing_field_accepted(self, "doseQuantity.unit")

    def test_post_reason_code_coding_code(self):
        """Test that the JSON data is accepted when reason_code_coding_code is absent"""
        sample_data_reason_code = self.covid_json_data["reasonCode"]
        for index in range(len(sample_data_reason_code)):
            MandationTests.test_missing_field_accepted(self, f"reasonCode[{index}].coding[0].code")

    def test_post_reason_code_coding_display(self):
        """Test that the JSON data is accepted when reason_code_coding_display is absent"""
        sample_data_reason_code = self.covid_json_data["reasonCode"]
        for index in range(len(sample_data_reason_code)):
            MandationTests.test_missing_field_accepted(self, f"reasonCode[{index}].coding[0].display")

    def test_post_nhs_number_verification_status_code(self):
        """Test that the JSON data is accepted when nhs_number_verification_status_code is absent"""
        field_location = (
            "contained[?(@.resourceType=='Patient')]"
            + ".identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]"
            + ".extension[?(@.url=="
            + "'https://fhir.hl7.org.uk/StructureDefinition/"
            + "Extension-UKCore-NHSNumberVerificationStatus')]"
            + ".valueCodeableConcept.coding[?(@.system=='https://fhir.hl7.org.uk/CodeSystem/"
            + "UKCore-NHSNumberVerificationStatusEngland')].code"
        )
        MandationTests.test_missing_mandatory_field_rejected(self, field_location)

    def test_post_nhs_number_verification_status_display(self):
        """
        Test that the JSON data is accepted when nhs_number_verification_status_display is absent
        """
        field_location = (
            "contained[?(@.resourceType=='Patient')]"
            + ".identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]"
            + ".extension[?(@.url=="
            + "'https://fhir.hl7.org.uk/StructureDefinition/"
            + "Extension-UKCore-NHSNumberVerificationStatus')]"
            + ".valueCodeableConcept.coding[?(@.system=='https://fhir.hl7.org.uk/CodeSystem/"
            + "UKCore-NHSNumberVerificationStatusEngland')].display"
        )

        MandationTests.test_missing_field_accepted(self, field_location)

    def test_post_organization_identifier_system(self):
        """
        Test that the JSON data is rejected if it does not contain organization_identifier_system
        """
        MandationTests.test_missing_mandatory_field_rejected(
            self, "performer[?(@.actor.type=='Organization')].actor.identifier.system"
        )

    def test_post_local_patient_value(self):
        """Test that the JSON data is rejected if it does not contain local_patient_value"""
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='LocalPatient')].answer[0].valueReference.identifier.value",
        )

    def test_post_local_patient_system(self):
        """Test that the JSON data is rejected if it does not contain local_patient_system"""
        MandationTests.test_missing_mandatory_field_rejected(
            self,
            field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='LocalPatient')].answer[0].valueReference.identifier.system",
        )

    def test_post_consent_code(self):
        """
        Test that present or absent consent_code is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='Consent')].answer[0].valueCoding.code"
        )

        # Test cases for COVID-19 and FLU
        for vaccine_type in [VaccineTypes.covid_19, VaccineTypes.flu]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.mandatory,
                mandation_when_status_entered_in_error=Mandation.mandatory,
                mandation_when_status_not_done=Mandation.required,
                expected_bespoke_error_message=f"{field_location} is mandatory when status is "
                + f"'completed' or 'entered-in-error' and vaccination type is {vaccine_type}",
                expected_error_type="MandatoryError",
            )

        # Test cases for HPV and MMR
        for vaccine_type in [VaccineTypes.hpv, VaccineTypes.mmr]:
            MandationTests.test_mandation_for_status_dependent_fields(
                self,
                field_location,
                vaccine_type=vaccine_type,
                mandation_when_status_completed=Mandation.required,
                mandation_when_status_entered_in_error=Mandation.required,
                mandation_when_status_not_done=Mandation.required,
            )

    def test_post_consent_display(self):
        """
        Test that present or absent consent_display is accepted or rejected
        as appropriate dependent on other fields
        """
        MandationTests.test_missing_field_accepted(
            self,
            field_location="contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='Consent')].answer[0].valueCoding.display",
        )

    def test_post_care_setting_code(self):
        """
        Test that present or absent care_setting_code is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='CareSetting')].answer[0].valueCoding.code"
        )

        # Test cases for COVID19
        MandationTests.test_missing_mandatory_field_rejected(
            self, field_location, valid_json_data=deepcopy(self.covid_json_data)
        )

        # Test cases for FLU
        MandationTests.test_missing_mandatory_field_rejected(
            self, field_location, valid_json_data=deepcopy(self.flu_json_data)
        )

        # Test cases for HPV
        MandationTests.test_missing_field_accepted(self, field_location, valid_json_data=deepcopy(self.hpv_json_data))

        # Test cases for MMR
        MandationTests.test_missing_field_accepted(self, field_location, valid_json_data=deepcopy(self.mmr_json_data))

    def test_post_care_setting_display(self):
        """
        Test that present or absent care_setting_display is accepted or rejected
        as appropriate dependent on other fields
        """
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='CareSetting')].answer[0].valueCoding.display"
        )

        for vaccine_type in [
            VaccineTypes.covid_19,
            VaccineTypes.flu,
            VaccineTypes.hpv,
            VaccineTypes.mmr,
        ]:
            if vaccine_type == VaccineTypes.covid_19:
                valid_json_data = deepcopy(self.covid_json_data)
            elif vaccine_type == VaccineTypes.flu:
                valid_json_data = deepcopy(self.flu_json_data)
            elif vaccine_type == VaccineTypes.mmr:
                valid_json_data = deepcopy(self.mmr_json_data)
            elif vaccine_type == VaccineTypes.hpv:
                valid_json_data = deepcopy(self.hpv_json_data)

            valid_json_data = MandationTests.update_vaccination_procedure_code(
                self, vaccine_type, valid_json_data=valid_json_data
            )
            MandationTests.test_missing_field_accepted(self, field_location, valid_json_data)

    def test_post_ip_address(self):
        """Test that the JSON data is rejected if it does contain ip_address"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='IpAddress')].answer[0].valueString"
        )

        # Test case for COVID19
        MandationTests.test_missing_field_accepted(self, field_location)

        # Test cases for FLU, HPV and MMR
        # Add value into the JSON data
        invalid_flu_json_data = deepcopy(self.flu_json_data)
        invalid_flu_json_data["contained"][2]["item"].append(
            {"linkId": "IpAddress", "answer": [{"valueString": "IP_ADDRESS"}]}
        )

        for vaccine_type in (VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            MandationTests.test_present_not_applicable_field_rejected(
                self,
                field_location=field_location,
                vaccine_type=vaccine_type,
                invalid_json_data=deepcopy(invalid_flu_json_data),
            )

    def test_post_user_id(self):
        """Test that the JSON data is rejected if it does contain user_id"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='UserId')].answer[0].valueString"
        )

        # Test case for COVID19
        MandationTests.test_missing_field_accepted(self, field_location)

        # Add value into the JSON data
        invalid_flu_json_data = deepcopy(self.flu_json_data)
        invalid_flu_json_data["contained"][2]["item"].append(
            {"linkId": "UserId", "answer": [{"valueString": "USER_ID"}]}
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in (VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            MandationTests.test_present_not_applicable_field_rejected(
                self,
                field_location=field_location,
                vaccine_type=vaccine_type,
                invalid_json_data=deepcopy(invalid_flu_json_data),
            )

    def test_post_user_name(self):
        """Test that the JSON data is rejected if it does contain user_name"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='UserName')].answer[0].valueString"
        )

        # Test case for COVID19
        MandationTests.test_missing_field_accepted(self, field_location)

        # Add value into the JSON data
        invalid_flu_json_data = deepcopy(self.flu_json_data)
        invalid_flu_json_data["contained"][2]["item"].append(
            {"linkId": "UserName", "answer": [{"valueString": "USER_NAME"}]}
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in (VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            MandationTests.test_present_not_applicable_field_rejected(
                self,
                field_location=field_location,
                vaccine_type=vaccine_type,
                invalid_json_data=deepcopy(invalid_flu_json_data),
            )

    def test_post_user_email(self):
        """Test that the JSON data is rejected if it does contain user_email"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='UserEmail')].answer[0].valueString"
        )

        # Test case for COVID19
        MandationTests.test_missing_field_accepted(self, field_location)

        # Add value into the JSON data
        invalid_flu_json_data = deepcopy(self.flu_json_data)
        invalid_flu_json_data["contained"][2]["item"].append(
            {"linkId": "UserEmail", "answer": [{"valueString": "USER_EMAIL"}]}
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in (VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            MandationTests.test_present_not_applicable_field_rejected(
                self,
                field_location=field_location,
                vaccine_type=vaccine_type,
                invalid_json_data=deepcopy(invalid_flu_json_data),
            )

    def test_post_submitted_time_stamp(self):
        """Test that the JSON data is rejected if it does contain submitted_time_stamp"""
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item"
            + "[?(@.linkId=='SubmittedTimeStamp')].answer[0].valueDateTime"
        )

        # Test case for COVID19
        MandationTests.test_missing_field_accepted(self, field_location)

        # Add value into the JSON data
        invalid_flu_json_data = deepcopy(self.flu_json_data)
        invalid_flu_json_data["contained"][2]["item"].append(
            {
                "linkId": "SubmittedTimeStamp",
                "answer": [{"valueDateTime": "2021-02-07T13:44:07+00:00"}],
            }
        )

        # Test cases for FLU, HPV and MMR
        for vaccine_type in (VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr):
            MandationTests.test_present_not_applicable_field_rejected(
                self,
                field_location=field_location,
                vaccine_type=vaccine_type,
                invalid_json_data=deepcopy(invalid_flu_json_data),
            )

    def test_post_location_identifier_value(self):
        """
        Test that the JSON data is rejected if it does and does not contain
        location_identifier_value as appropriate
        """
        field_location = "location.identifier.value"
        # Test cases for COVID-19, FLU and HPV where it is mandatory
        for vaccine_type in (VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv):
            valid_json_data = MandationTests.update_vaccination_procedure_code(
                self,
                vaccine_type,
                valid_json_data=deepcopy(
                    self.covid_json_data if vaccine_type == VaccineTypes.covid_19 else self.flu_json_data
                ),
            )
            MandationTests.test_missing_mandatory_field_rejected(self, field_location, valid_json_data=valid_json_data)

        # Test cases for MMR where it is N/A
        invalid_json_data = MandationTests.update_vaccination_procedure_code(
            self, VaccineTypes.mmr, valid_json_data=deepcopy(self.flu_json_data)
        )
        invalid_json_data["location"] = {
            "identifier": {
                "value": "X99999",
            }
        }
        MandationTests.test_present_not_applicable_field_rejected(
            self,
            field_location,
            VaccineTypes.mmr,
            invalid_json_data=invalid_json_data,
        )

    def test_post_location_identifier_system(self):
        """
        Test that the JSON data is rejected if it does and does not contain
        location_identifier_system as appropriate
        """
        field_location = "location.identifier.system"
        # Test cases for COVID-19, FLU and HPV where it is mandatory
        for vaccine_type in (VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv):
            valid_json_data = MandationTests.update_vaccination_procedure_code(
                self,
                vaccine_type,
                valid_json_data=deepcopy(
                    self.covid_json_data if vaccine_type == VaccineTypes.covid_19 else self.flu_json_data
                ),
            )
            MandationTests.test_missing_mandatory_field_rejected(self, field_location, valid_json_data=valid_json_data)

        # Test cases for MMR where it is N/A
        invalid_json_data = MandationTests.update_vaccination_procedure_code(
            self, VaccineTypes.mmr, valid_json_data=deepcopy(self.flu_json_data)
        )
        invalid_json_data["location"] = {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
            }
        }
        MandationTests.test_present_not_applicable_field_rejected(
            self,
            field_location,
            VaccineTypes.mmr,
            invalid_json_data=invalid_json_data,
        )

    def test_post_reduce_validation_code(self):
        """
        Test that present or absent reduce_validation_code is accepted
        """
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='ReduceValidationCode')].answer[0].valueString"
        )
        MandationTests.test_missing_field_accepted(
            self,
            field_location,
        )
        MandationTests.test_present_field_accepted(
            self,
            valid_json_data=deepcopy(self.covid_json_data),
        )
