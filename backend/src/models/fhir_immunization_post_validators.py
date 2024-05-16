"FHIR Immunization Post Validators"

from mappings import Mandation, VaccineTypes, vaccine_type_applicable_validations
from models.constants import Constants
from models.utils.generic_utils import (
    get_generic_questionnaire_response_value_from_model,
    get_generic_extension_value_from_model,
    generate_field_location_for_questionnaire_response,
    generate_field_location_for_extension,
    get_contained_resource_from_model,
    is_organization,
    get_nhs_number_verification_status_code,
    get_target_disease_codes_from_model,
)
from models.utils.validation_utils import disease_codes_to_vaccine_type
from models.utils.post_validation_utils import PostValidation, MandatoryError


check_mandation_requirements_met = PostValidation.check_mandation_requirements_met
get_generic_field_value = PostValidation.get_generic_field_value
get_generic_questionnaire_response_value = PostValidation.get_generic_questionnaire_response_value


class PostValidators:
    """FHIR Immunization Post Validators"""

    def __init__(self, immunization):
        self.immunization = immunization
        self.errors = []
        self.vaccine_type: str
        # Note: FHIR validator mandates the presence of status field, so there is no post-validation for status
        self.status = self.immunization.status

    def validate(self):
        """Run all post-validation checks."""
        # Vaccine_type is a critical validation that other validations rely on, if it fails then no need to carry on
        try:
            self.validate_and_set_vaccine_type(self.immunization)
        except (ValueError, TypeError, IndexError, AttributeError, MandatoryError) as e:
            raise ValueError(str(e)) from e

        validation_methods = [
            self.validate_occurrence_date_time,
            self.validate_patient_identifier_value,
            self.validate_patient_name_given,
            self.validate_patient_name_family,
            self.validate_patient_birth_date,
            self.validate_patient_gender,
            self.validate_patient_address_postal_code,
            self.validate_organization_identifier_value,
            self.validate_organization_display,
            self.validate_identifier_value,
            self.validate_identifier_system,
            self.validate_practitioner_name_given,
            self.validate_practitioner_name_family,
            self.validate_practitioner_identifier_value,
            self.validate_practitioner_identifier_system,
            self.validate_performer_sds_job_role,
            self.validate_recorded,
            self.validate_primary_source,
            self.validate_report_origin_text,
            self.validate_vaccination_procedure_code,
            self.validate_vaccination_procedure_display,
            self.validate_vaccination_situation_code,
            self.validate_vaccination_situation_display,
            self.validate_status_reason_coding_code,
            self.validate_status_reason_coding_display,
            self.validate_protocol_applied_dose_number_positive_int,
            self.validate_vaccine_code_coding_code,
            self.validate_vaccine_code_coding_display,
            self.validate_manufacturer_display,
            self.validate_lot_number,
            self.validate_expiration_date,
            self.validate_site_coding_code,
            self.validate_site_coding_display,
            self.validate_route_coding_code,
            self.validate_route_coding_display,
            self.validate_dose_quantity_value,
            self.validate_dose_quantity_code,
            self.validate_dose_quantity_unit,
            self.validate_reason_code_coding_code,
            self.validate_reason_code_coding_display,
            self.validate_nhs_number_verification_status_code,
            self.validate_nhs_number_verification_status_display,
            self.validate_organization_identifier_system,
            self.validate_local_patient_value,
            self.validate_local_patient_system,
            self.validate_consent_code,
            self.validate_consent_display,
            self.validate_care_setting_code,
            self.validate_care_setting_display,
            self.validate_ip_address,
            self.validate_user_id,
            self.validate_user_name,
            self.validate_user_email,
            self.validate_submitted_time_stamp,
            self.validate_location_identifier_value,
            self.validate_location_identifier_system,
            self.validate_reduce_validation_reason,
        ]
        for method in validation_methods:
            try:
                method(self.immunization)
            except (ValueError, TypeError, IndexError, AttributeError, MandatoryError) as e:
                self.errors.append(str(e))

        if self.errors:
            all_errors = "; ".join(self.errors)
            raise ValueError(all_errors)

    def validate_and_set_vaccine_type(self, values: dict) -> dict:
        """
        Validate that the combination of targetDisease codes maps to a valid vaccine type and
        set the vaccine type accordingly
        """
        field_location = "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"

        try:
            target_diseases = get_target_disease_codes_from_model(values)
            if target_diseases == []:
                raise MandatoryError
            self.vaccine_type = disease_codes_to_vaccine_type(target_diseases)
        except (KeyError, IndexError, TypeError, MandatoryError) as error:
            raise MandatoryError(f"{field_location} is a mandatory field") from error

    def validate_patient_identifier_value(self, values: dict) -> dict:
        "Validate that patient_identifier_value is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Patient')].identifier[0].value"

        try:
            contained_patient = get_contained_resource_from_model(values, "Patient")

            field_value = next(
                x for x in contained_patient.identifier if x.system == "https://fhir.nhs.uk/Id/nhs-number"
            ).value
            # TODO: BUG Fix this. Should have a separate try-excpet for verification_status_code. Also consider
            # whether logic can be made more consistent with other CM fields (note that NHS_NUMBER is R, not CM)
            verification_status_code = get_nhs_number_verification_status_code(values)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        if not field_value and verification_status_code != "04":
            raise MandatoryError(f"{field_location} is mandatory when verification status is not 04")

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="patient_identifier_value"
        )

    def validate_patient_name_given(self, values: dict) -> dict:
        "Validate that patient_name_given is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Patient')].name[0].given"

        try:
            field_value = get_contained_resource_from_model(values, "Patient").name[0].given
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="patient_name_given"
        )

    def validate_patient_name_family(self, values: dict) -> dict:
        "Validate that patient_name_family is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Patient')].name[0].family"

        try:
            field_value = get_contained_resource_from_model(values, "Patient").name[0].family
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="patient_name_family"
        )

    def validate_patient_birth_date(self, values: dict) -> dict:
        "Validate that patient_birth_date is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Patient')].birthDate"

        try:
            field_value = get_contained_resource_from_model(values, "Patient").birthDate
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="patient_birth_date"
        )

    def validate_patient_gender(self, values: dict) -> dict:
        "Validate that patient_gender is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Patient')].gender"

        try:
            field_value = get_contained_resource_from_model(values, "Patient").gender
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="patient_gender"
        )

    def validate_patient_address_postal_code(self, values: dict) -> dict:
        "Validate that patient_address_postal_code is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Patient')].address[0].postalCode"

        try:
            field_value = get_contained_resource_from_model(values, "Patient").address[0].postalCode
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="patient_address_postal_code"
        )

    def validate_occurrence_date_time(self, values: dict) -> dict:
        "Validate that occurrence_date_time is present or absent, as required"
        field_location = "occurenceDateTime"

        field_value = get_generic_field_value(values, key="occurrenceDateTime")

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="occurrence_date_time"
        )

    def validate_organization_identifier_value(self, values: dict) -> dict:
        """Validate that organization_identifier_value is present or absent, as required"""
        field_location = "performer[?(@.actor.type=='Organization')].actor.identifier.value"

        try:
            field_value = [x for x in values.performer if is_organization(x)][0].actor.identifier.value
        except (KeyError, IndexError, AttributeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="organization_identifier_value"
        )

    def validate_organization_display(self, values: dict) -> dict:
        """Validate that organization_display is present or absent, as required"""
        field_location = "performer[?(@.actor.type=='Organization')].actor.display"

        try:
            field_value = [x for x in values.performer if is_organization(x)][0].actor.display
        except (KeyError, IndexError, AttributeError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="organization_display"
        )

    def validate_identifier_value(self, values: dict) -> dict:
        "Validate that identifier_value is present or absent, as required"
        field_location = "identifier[0].value"

        field_value = get_generic_field_value(values, "identifier", index=0, attribute="value")

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="identifier_value"
        )

    def validate_identifier_system(self, values: dict) -> dict:
        "Validate that identifier_system is present or absent, as required"
        field_location = "identifier[0].system"

        field_value = get_generic_field_value(values, "identifier", index=0, attribute="system")

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="identifier_system"
        )

    def validate_practitioner_name_given(self, values: dict) -> dict:
        "Validate that practitioner_name_given is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Practitioner')].name[0].given"

        try:
            field_value = get_contained_resource_from_model(values, "Practitioner").name[0].given
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="practitioner_name_given"
        )

    def validate_practitioner_name_family(self, values: dict) -> dict:
        "Validate that practitioner_name_family is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Practitioner')].name[0].family"

        try:
            field_value = get_contained_resource_from_model(values, "Practitioner").name[0].family
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="practitioner_name_family"
        )

    def validate_practitioner_identifier_value(self, values: dict) -> dict:
        "Validate that practitioner_identifier_value is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Practitioner')].identifier[0].value"

        try:
            field_value = get_contained_resource_from_model(values, "Practitioner").identifier[0].value
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="practitioner_identifier_value"
        )

    def validate_practitioner_identifier_system(self, values: dict) -> dict:
        "Validate that practitioner_identifier_system is present or absent, as required"
        field_location = "contained[?(@.resourceType=='Practitioner')].identifier[0].system"

        try:
            practitioner_identifier_system = (
                get_contained_resource_from_model(values, "Practitioner").identifier[0].system
            )
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            practitioner_identifier_system = None

        # Set up mandation defaults
        mandation = vaccine_type_applicable_validations["practitioner_identifier_system"]
        bespoke_mandatory_error_message = None

        # Handle conditional mandation logic
        try:
            practitioner_identifier_value = (
                get_contained_resource_from_model(values, "Practitioner").identifier[0].value
            )
        except (KeyError, IndexError, AttributeError):
            practitioner_identifier_value = None

        # If practioner_identifier_value is present and vaccine type is COVID19 or FLU,
        # then practitioner_identifier_system is mandatory
        if practitioner_identifier_value and (
            self.vaccine_type == VaccineTypes.covid_19 or self.vaccine_type == VaccineTypes.flu
        ):
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when contained"
                + "[?(@.resourceType=='Practitioner')].identifier[0].value is present"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.optional

        check_mandation_requirements_met(
            field_value=practitioner_identifier_system,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_performer_sds_job_role(self, values: dict) -> dict:
        "Validate that performer_sds_job_role is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='PerformerSDSJobRole')].answer[0].valueString"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(
                values, "PerformerSDSJobROle", "valueString"
            )
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="performer_sds_job_role"
        )

    def validate_recorded(self, values: dict) -> dict:
        "Validate that recorded is present or absent, as required"
        field_value = get_generic_field_value(values, key="recorded")

        check_mandation_requirements_met(
            field_value, field_location="recorded", vaccine_type=self.vaccine_type, mandation_key="recorded"
        )

    def validate_primary_source(self, values: dict) -> dict:
        "Validate that primary_source is present or absent, as required"
        field_value = get_generic_field_value(values, key="primarySource")

        check_mandation_requirements_met(
            field_value, field_location="primarySource", vaccine_type=self.vaccine_type, mandation_key="primary_source"
        )

    def validate_report_origin_text(self, values: dict) -> dict:
        "Validate that report_origin_text is present or absent, as required"
        field_location = "reportOrigin.text"

        field_value = get_generic_field_value(values, key="reportOrigin", attribute="text")

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["report_origin_text"][self.vaccine_type]
        if not values.primarySource:
            mandation = Mandation.mandatory

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=f"{field_location} is mandatory when primarySource is false",
        )

    def validate_vaccination_procedure_code(self, values: dict) -> dict:
        "Validate that vaccination_procedure_code is a valid code"
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
        system = "http://snomed.info/sct"
        field_type = "code"
        field_location = generate_field_location_for_extension(url, system, field_type)

        try:
            field_value = get_generic_extension_value_from_model(values, url, system, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="vaccination_procedure_code"
        )

    def validate_vaccination_procedure_display(self, values: dict) -> dict:
        "Validate that vaccination_procedure_display is present or absent, as required"
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
        system = "http://snomed.info/sct"
        field_type = "display"
        field_location = generate_field_location_for_extension(url, system, field_type)

        try:
            field_value = get_generic_extension_value_from_model(values, url, system, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="vaccination_procedure_display"
        )

    def validate_vaccination_situation_code(self, values: dict) -> dict:
        "Validate that vaccination_situation_code is present or absent, as required"
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation"
        system = "http://snomed.info/sct"
        field_type = "code"
        field_location = generate_field_location_for_extension(url, system, field_type)

        try:
            field_value = get_generic_extension_value_from_model(values, url, system, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["vaccination_situation_code"][self.vaccine_type]
        if values.status == "not-done":
            mandation = Mandation.mandatory
        else:
            mandation = Mandation.optional

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=f"{field_location} is mandatory when status is 'not-done'",
        )

    def validate_vaccination_situation_display(self, values: dict) -> dict:
        "Validate that vaccination_situation_display is present or absent, as required"
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation"
        system = "http://snomed.info/sct"
        field_type = "display"
        field_location = generate_field_location_for_extension(url, system, field_type)

        try:
            field_value = get_generic_extension_value_from_model(values, url, system, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="vaccination_situation_display"
        )

    def validate_status_reason_coding_code(self, values: dict) -> dict:
        "Validate that vaccination_situation_code is present or absent, as required"
        field_location = "statusReason.coding[?(@.system=='http://snomed.info/sct')].code"

        try:
            field_value = [x for x in values.statusReason.coding if x.system == "http://snomed.info/sct"][0].code
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["status_reason_coding_code"][self.vaccine_type]
        if values.status == "not-done":
            mandation = Mandation.mandatory
        else:
            mandation = Mandation.optional

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=f"{field_location} is mandatory when status is 'not-done'",
        )

    def validate_status_reason_coding_display(self, values: dict) -> dict:
        "Validate that status_reason_coding_display is present or absent, as required"
        field_location = "statusReason.coding[?(@.system=='http://snomed.info/sct')].display"

        try:
            field_value = [x for x in values["statusReason"].coding if x.system == "http://snomed.info/sct"][0].code
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="status_reason_coding_display"
        )

    def validate_protocol_applied_dose_number_positive_int(self, values: dict) -> dict:
        "Validate that protocol_applied_dose_number_positive_int is present or absent, as required"
        field_location = "protocolApplied[0].doseNumberPositiveInt"

        try:
            field_value = values.protocolApplied[0].doseNumberPositiveInt
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["protocol_applied_dose_number_positive_int"][self.vaccine_type]

        if self.vaccine_type == VaccineTypes.flu:
            mandation = Mandation.mandatory if values.status != "not-done" else Mandation.required

        # Set the bespoke mandatory error messages
        bespoke_mandatory_error_message = None
        if self.vaccine_type == VaccineTypes.covid_19:
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when vaccination type is {self.vaccine_type}"
            )
        if self.vaccine_type == VaccineTypes.flu:
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is"
                + f" 'completed' or 'entered-in-error' and vaccination type is {self.vaccine_type}"
            )

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_vaccine_code_coding_code(self, values: dict) -> dict:
        "Validate that vaccineCode_coding_code is present or absent, as required"
        if self.status == "not-done":
            system = "http://terminology.hl7.org/CodeSystem/v3-NullFlavor"
        else:
            system = "http://snomed.info/sct"
        field_location = f"vaccineCode.coding[?(@.system=='{system}')].code"

        try:
            field_value = next((x.code for x in values.vaccineCode.coding if x.system == system), None)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="vaccine_code_coding_code"
        )

        if self.status == "not-done" and field_value not in Constants.NOT_DONE_VACCINE_CODES:
            raise ValueError(
                f"{field_location} must be one of the following: {str(', '.join(Constants.NOT_DONE_VACCINE_CODES))}"
                + " when status is 'not-done'"
            )

    def validate_vaccine_code_coding_display(self, values: dict) -> dict:
        "Validate that vaccineCode_coding_display is present or absent, as required"
        field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display"

        try:
            field_value = [x for x in values["vaccineCode"].coding if x.system == "http://snomed.info/sct"][0].display
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="vaccine_code_coding_display"
        )

    def validate_manufacturer_display(self, values: dict) -> dict:
        "Validate that manufacturer_display is present or absent, as required"
        field_location = "manufacturer.display"

        try:
            manufacturer_display = values.manufacturer.display
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            manufacturer_display = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["manufacturer_display"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type == VaccineTypes.covid_19:
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.required

        check_mandation_requirements_met(
            field_value=manufacturer_display,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_lot_number(self, values: dict) -> dict:
        "Validate that lot_number is present or absent, as required"
        field_location = "lotNumber"

        try:
            field_value = values.lotNumber
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["lot_number"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type == VaccineTypes.covid_19:
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.required

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_expiration_date(self, values: dict) -> dict:
        "Validate that expiration_date is present or absent, as required"
        field_location = "expirationDate"

        try:
            expiration_date = values.expirationDate
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            expiration_date = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["expiration_date"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type == VaccineTypes.covid_19:
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.required

        check_mandation_requirements_met(
            field_value=expiration_date,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_site_coding_code(self, values: dict) -> dict:
        "Validate that site_coding_code is present or absent, as required"
        field_location = "site.coding[?(@.system=='http://snomed.info/sct')].code"

        try:
            site_coding_code = [x for x in values["site"].coding if x.system == "http://snomed.info/sct"][0].code
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            site_coding_code = None

        check_mandation_requirements_met(
            site_coding_code, field_location, vaccine_type=self.vaccine_type, mandation_key="site_coding_code"
        )

    def validate_site_coding_display(self, values: dict) -> dict:
        "Validate that site.coding.display is present or absent, as required"
        field_location = "site.coding[?(@.system=='http://snomed.info/sct')].display"

        try:
            site_coding_display = [x for x in values["site"].coding if x.system == "http://snomed.info/sct"][0].display
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            site_coding_display = None

        check_mandation_requirements_met(
            site_coding_display, field_location, vaccine_type=self.vaccine_type, mandation_key="site_coding_display"
        )

    def validate_route_coding_code(self, values: dict) -> dict:
        "Validate that route_coding_code is present or absent, as required"
        field_location = "route.coding[?(@.system=='http://snomed.info/sct')].code"

        try:
            route_coding_code = [x for x in values.route.coding if x.system == "http://snomed.info/sct"][0].code
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            route_coding_code = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["route_coding_code"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type in (
            VaccineTypes.covid_19,
            VaccineTypes.flu,
        ):
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.required

        check_mandation_requirements_met(
            field_value=route_coding_code,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_route_coding_display(self, values: dict) -> dict:
        "Validate that route_coding_display is present or absent, as required"
        field_location = "route.coding[?(@.system=='http://snomed.info/sct')].display"

        try:
            route_coding_display = [x for x in values["route"].coding if x.system == "http://snomed.info/sct"][
                0
            ].display
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            route_coding_display = None

        check_mandation_requirements_met(
            route_coding_display, field_location, vaccine_type=self.vaccine_type, mandation_key="route_coding_display"
        )

    def validate_dose_quantity_value(self, values: dict) -> dict:
        "Validate that dose_quantity_value is present or absent, as required"
        field_location = "doseQuantity.value"

        try:
            dose_quantity_value = values.doseQuantity.value
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            dose_quantity_value = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["dose_quantity_value"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type in (
            VaccineTypes.covid_19,
            VaccineTypes.flu,
        ):
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.required

        check_mandation_requirements_met(
            field_value=dose_quantity_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_dose_quantity_code(self, values: dict) -> dict:
        "Validate that dose_quantity_code is present or absent, as required"
        field_location = "doseQuantity.code"

        try:
            dose_quantity_code = values.doseQuantity.code
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            dose_quantity_code = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["dose_quantity_code"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type in (
            VaccineTypes.covid_19,
            VaccineTypes.flu,
        ):
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.required

        check_mandation_requirements_met(
            field_value=dose_quantity_code,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_dose_quantity_unit(self, values: dict) -> dict:
        "Validate that dose_quantity_unit is present or absent, as required"
        field_location = "doseQuantity.unit"

        try:
            field_value = values["doseQuantity"].unit
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="dose_quantity_unit"
        )

    def validate_reason_code_coding_code(self, values: dict) -> dict:
        "Validate that reason_code_coding_code is present or absent, as required"
        # The for loop must be run at least once to check for mandation, regardless of whether
        # reasonCode exists. If there are multiple items in reasonCode, then the loop must be
        # run over each of those items.
        number_of_iterations = len(values.reasonCode) if values.reasonCode else 1
        for index in range(number_of_iterations):
            field_location = f"reasonCode[{index}].coding[0].code"

            try:
                field_value = values["reasonCode"][index].coding[0].code
            except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
                field_value = None

            check_mandation_requirements_met(
                field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="reason_code_coding_code"
            )

    def validate_reason_code_coding_display(self, values: dict) -> dict:
        "Validate that reason_code_coding_display is present or absent, as required"
        # The for loop must be run at least once to check for mandation, regardless of whether
        # reasonCode exists. If there are multiple items in reasonCode, then the loop must be
        # run over each of those items.
        number_of_iterations = len(values.reasonCode) if values.reasonCode else 1
        for index in range(number_of_iterations):
            field_location = f"reasonCode[{index}].coding[0].display"

            try:
                field_value = values["reasonCode"][index].coding[0].display
            except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
                field_value = None

            check_mandation_requirements_met(
                field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="reason_code_coding_display"
            )

    def validate_nhs_number_verification_status_code(self, values: dict) -> dict:
        "Validate that nhs_number_verification_status_code is present or absent, as required"
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
        system = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
        field_type = "code"
        field_location = (
            "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
            + generate_field_location_for_extension(url, system, field_type)
        )

        try:
            patient_identifier = get_contained_resource_from_model(values, "Patient").identifier

            patient_identifier_extension_item = [
                x for x in patient_identifier if x.system == "https://fhir.nhs.uk/Id/nhs-number"
            ][0].extension

            value_codeable_concept_coding = [x for x in patient_identifier_extension_item if x.url == url][
                0
            ].valueCodeableConcept.coding

            field_value = [x for x in value_codeable_concept_coding if x.system == system][0].code
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            vaccine_type=self.vaccine_type,
            mandation_key="nhs_number_verification_status_code",
        )

    def validate_nhs_number_verification_status_display(self, values: dict) -> dict:
        "Validate that nhs_number_verification_status_display is present or absent, as required"
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
        system = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
        field_type = "display"
        field_location = (
            "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
            + generate_field_location_for_extension(url, system, field_type)
        )

        try:
            patient_identifier = get_contained_resource_from_model(values, "Patient").identifier

            patient_identifier_extension_item = [
                x for x in patient_identifier if x.system == "https://fhir.nhs.uk/Id/nhs-number"
            ][0].extension

            value_codeable_concept_coding = [x for x in patient_identifier_extension_item if x.url == url][
                0
            ].valueCodeableConcept.coding

            nhs_number_verification_status_display = [x for x in value_codeable_concept_coding if x.system == system][
                0
            ].display
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            nhs_number_verification_status_display = None

        check_mandation_requirements_met(
            field_value=nhs_number_verification_status_display,
            field_location=field_location,
            vaccine_type=self.vaccine_type,
            mandation_key="nhs_number_verification_status_display",
        )

    def validate_organization_identifier_system(self, values: dict) -> dict:
        """Validate that organization_identifier_system is present or absent, as required"""
        field_location = "performer[?(@.actor.type=='Organization')].actor.identifier.system"

        try:
            field_value = [x for x in values.performer if is_organization(x)][0].actor.identifier.system
        except (KeyError, IndexError, AttributeError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="organization_identifier_system"
        )

    def validate_local_patient_value(self, values: dict) -> dict:
        """Validate that local_patient_value is present or absent, as required"""
        link_id = "LocalPatient"
        answer_type = "valueReference"
        field_type = "value"
        field_location = generate_field_location_for_questionnaire_response(link_id, answer_type, field_type)

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="local_patient_value"
        )

    def validate_local_patient_system(self, values: dict) -> dict:
        """Validate that local_patient_system is present or absent, as required"""
        link_id = "LocalPatient"
        answer_type = "valueReference"
        field_type = "system"
        field_location = generate_field_location_for_questionnaire_response(link_id, answer_type, field_type)

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="local_patient_system"
        )

    def validate_consent_code(self, values: dict) -> dict:
        "Validate that consent_code is present or absent, as required"
        link_id = "Consent"
        answer_type = "valueCoding"
        field_type = "code"
        field_location = generate_field_location_for_questionnaire_response(link_id, answer_type, field_type)

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        # Handle conditional mandation logic
        mandation = vaccine_type_applicable_validations["consent_code"][self.vaccine_type]
        bespoke_mandatory_error_message = None

        if values.status != "not-done" and self.vaccine_type in (
            VaccineTypes.covid_19,
            VaccineTypes.flu,
        ):
            mandation = Mandation.mandatory
            bespoke_mandatory_error_message = (
                f"{field_location} is mandatory when status is 'completed' or 'entered-in-error'"
                + f" and vaccination type is {self.vaccine_type}"
            )
        else:
            mandation = Mandation.optional

        check_mandation_requirements_met(
            field_value=field_value,
            field_location=field_location,
            mandation=mandation,
            bespoke_mandatory_error_message=bespoke_mandatory_error_message,
        )

    def validate_consent_display(self, values: dict) -> dict:
        "Validate that consent_display is present or absent, as required"
        link_id = "Consent"
        answer_type = "valueCoding"
        field_type = "display"
        field_location = generate_field_location_for_questionnaire_response(link_id, answer_type, field_type)

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="consent_display"
        )

    def validate_care_setting_code(self, values: dict) -> dict:
        "Validate that care_setting_code is present or absent, as required"
        link_id = "CareSetting"
        answer_type = "valueCoding"
        field_type = "code"
        field_location = generate_field_location_for_questionnaire_response(link_id, answer_type, field_type)

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="care_setting_code"
        )

    def validate_care_setting_display(self, values: dict) -> dict:
        "Validate that care_setting_display is present or absent, as required"
        link_id = "CareSetting"
        answer_type = "valueCoding"
        field_type = "display"
        field_location = generate_field_location_for_questionnaire_response(link_id, answer_type, field_type)

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="care_setting_display"
        )

    def validate_ip_address(self, values: dict) -> dict:
        "Validate that ip_address is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='IpAddress')].answer[0].valueString"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, "IpAddress", "valueString")
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="ip_address"
        )

    def validate_user_id(self, values: dict) -> dict:
        "Validate that user_id is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='UserId')].answer[0].valueString"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, "UserId", "valueString")
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="user_id"
        )

    def validate_user_name(self, values: dict) -> dict:
        "Validate that user_name is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='UserName')].answer[0].valueString"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, "UserName", "valueString")
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="user_name"
        )

    def validate_user_email(self, values: dict) -> dict:
        "Validate that user_email is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='UserEmail')].answer[0].valueString"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, "UserEmail", "valueString")
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="user_email"
        )

    def validate_submitted_time_stamp(self, values: dict) -> dict:
        "Validate that submitted_time_stamp is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='SubmittedTimeStamp')].answer[0].valueDateTime"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(
                values, "SubmittedTimeStamp", "valueDateTime"
            )
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="submitted_time_stamp"
        )

    def validate_location_identifier_value(self, values: dict) -> dict:
        "Validate that location_identifier_value is present or absent, as required"
        field_location = "location.identifier.value"

        try:
            field_value = values.location.identifier.value
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="location_identifier_value"
        )

    def validate_location_identifier_system(self, values: dict) -> dict:
        "Validate that location_identifier_system is present or absent, as required"
        field_location = "location.identifier.system"

        try:
            field_value = values.location.identifier.system
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="location_identifier_system"
        )

    def validate_reduce_validation_reason(self, values: dict) -> dict:
        "Validate that reduce_validation_reason is present or absent, as required"
        field_location = (
            "contained[?(@.resourceType=='QuestionnaireResponse')]"
            + ".item[?(@.linkId=='ReduceValidationReason')].answer[0].valueString"
        )

        try:
            field_value = get_generic_questionnaire_response_value_from_model(
                values, "ReduceValidationReason", "valueString"
            )
        except (KeyError, IndexError, AttributeError, MandatoryError, TypeError):
            field_value = None

        check_mandation_requirements_met(
            field_value, field_location, vaccine_type=self.vaccine_type, mandation_key="reduce_validation_reason"
        )
