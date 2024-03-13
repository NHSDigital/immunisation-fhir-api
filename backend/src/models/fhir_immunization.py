"""Immunization FHIR R4B validator"""

from typing import Literal

from fhir.resources.R4B.immunization import Immunization
from models.fhir_immunization_post_validators import FHIRImmunizationPostValidators
from models.fhir_immunization_pre_validators import FHIRImmunizationPreValidators
from models.utils.generic_utils import get_generic_questionnaire_response_value
from timer import timed

class ImmunizationValidator:
    """
    Validate the FHIR Immunization model against the NHS specific validators and Immunization
    FHIR profile
    """

    def __init__(self, add_post_validators: bool = True) -> None:
        class NewImmunization(Immunization):
            """
            Workaround for tests so we can instantiate our own instance of Immunization, and add
            the pre/post validators independently without affecting other tests
            """

        self.immunization = NewImmunization
        self.reduce_validation_code = False
        self.add_post_validators = add_post_validators

    def add_custom_root_pre_validators(self):
        """
        Add custom NHS validators to the model

        NOTE: THE ORDER IN WHICH THE VALIDATORS ARE ADDED IS IMPORTANT! DO NOT CHANGE THE ORDER
        WITHOUT UNDERSTANDING THE IMPACT ON OTHER VALIDATORS IN THE LIST.
        """
        # DO NOT CHANGE THE ORDER WITHOUT UNDERSTANDING THE IMPACT ON OTHER VALIDATORS IN THE LIST
        if not hasattr(self.immunization, "pre_validate_patient_identifier_value"):
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_contained, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_patient_reference, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_identifier, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_identifier_value,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_patient_name, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_name_given, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_name_family, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_birth_date, pre=True
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_patient_gender, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_patient_address, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_address_postal_code,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_occurrence_date_time,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_questionnaire_response_item,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_questionnaire_answers,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_performer_actor_type,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_performer_actor_reference,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_organization_identifier_value,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_organization_display,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_identifier, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_identifier_value, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_identifier_system, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_status, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_practitioner_name, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_practitioner_name_given,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_practitioner_name_family,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_practitioner_identifier,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_practitioner_identifier_value,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_practitioner_identifier_system,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_performer_sds_job_role,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_recorded, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_primary_source, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_report_origin_text, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_extension_urls,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_extension_value_codeable_concept_codings,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccination_procedure_code,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccination_procedure_display,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccination_situation_code,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccination_situation_display,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_status_reason_coding,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_status_reason_coding_code,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_status_reason_coding_display,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_protocol_applied, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_protocol_applied_dose_number_positive_int,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccine_code_coding, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccine_code_coding_code,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_vaccine_code_coding_display,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_manufacturer_display,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_lot_number, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_expiration_date, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_site_coding, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_site_coding_code, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_site_coding_display, pre=True
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_route_coding, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_route_coding_code, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_route_coding_display,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_dose_quantity_value, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_dose_quantity_code, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_dose_quantity_unit, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_reason_code_codings, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_reason_code_coding_codes,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_reason_code_coding_displays,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_patient_identifier_extension,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_nhs_number_verification_status_coding,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_nhs_number_verification_status_code,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_nhs_number_verification_status_display,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_organization_identifier_system,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_local_patient_value, pre=True
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_local_patient_system,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_consent_code, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_consent_display, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_care_setting_code, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_care_setting_display,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_ip_address, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_user_id, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_user_name, pre=True)
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_user_email, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_submitted_time_stamp,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_location_identifier_value,
                pre=True,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_location_identifier_system,
                pre=True,
            )
            self.immunization.add_root_validator(FHIRImmunizationPreValidators.pre_validate_reduce_validation, pre=True)
            self.immunization.add_root_validator(
                FHIRImmunizationPreValidators.pre_validate_reduce_validation_reason,
                pre=True,
            )

    def set_reduce_validation_code(self, json_data):
        """Set the reduce validation code"""
        reduce_validation_code = False

        # If reduce_validation_code field exists then retrieve it's value
        try:
            reduce_validation_code = get_generic_questionnaire_response_value(
                json_data, "ReduceValidation", "valueBoolean"
            )
        except (KeyError, IndexError, AttributeError, TypeError):
            pass
        finally:
            # If no value is given, then ReduceValidation default value is False
            if reduce_validation_code is None:
                reduce_validation_code = False

        self.reduce_validation_code = reduce_validation_code

    def add_custom_root_post_validators(self):
        """
        Add custom NHS post validators to the model

        NOTE: THE ORDER IN WHICH THE VALIDATORS ARE ADDED IS IMPORTANT! DO NOT CHANGE THE ORDER
        WITHOUT UNDERSTANDING THE IMPACT ON OTHER VALIDATORS IN THE LIST.
        """
        skip_on_failure = True
        # DO NOT CHANGE THE ORDER WITHOUT UNDERSTANDING THE IMPACT ON OTHER VALIDATORS IN THE LIST
        if not hasattr(self.immunization, "validate_and_set_vaccination_procedure_code"):
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_and_set_vaccination_procedure_code,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.set_status,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_patient_identifier_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_patient_name_given,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_patient_name_family,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_patient_birth_date,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_patient_gender,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_patient_address_postal_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_occurrence_date_time,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_organization_identifier_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_organization_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_identifier_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_identifier_system,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_practitioner_name_given,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_practitioner_name_family,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_practitioner_identifier_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_practitioner_identifier_system,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_performer_sds_job_role,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_recorded,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_primary_source,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_report_origin_text,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_vaccination_procedure_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_vaccination_situation_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_vaccination_situation_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_status_reason_coding_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_status_reason_coding_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_protocol_applied_dose_number_positive_int,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_vaccine_code_coding_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_vaccine_code_coding_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_manufacturer_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_lot_number,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_expiration_date,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_site_coding_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_site_coding_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_route_coding_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_route_coding_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_dose_quantity_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_dose_quantity_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_dose_quantity_unit,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_reason_code_coding_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_reason_code_coding_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_nhs_number_verification_status_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_nhs_number_verification_status_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_organization_identifier_system,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_local_patient_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_local_patient_system,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_consent_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_consent_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_care_setting_code,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_care_setting_display,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_ip_address,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_user_id,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_user_name,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_user_email,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_submitted_time_stamp,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_location_identifier_value,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_location_identifier_system,
                skip_on_failure=skip_on_failure,
            )
            self.immunization.add_root_validator(
                FHIRImmunizationPostValidators.validate_reduce_validation_reason,
                skip_on_failure=skip_on_failure,
            )

    def remove_custom_root_validators(self, mode: Literal["pre", "post"]):
        """Remove custom NHS validators from the model"""
        if mode == "pre":
            for validator in self.immunization.__pre_root_validators__:
                if "FHIRImmunizationPreValidators" in str(validator):
                    self.immunization.__pre_root_validators__.remove(validator)
        elif mode == "post":
            for validator in self.immunization.__post_root_validators__:
                if "FHIRImmunizationPostValidators" in str(validator):
                    self.immunization.__post_root_validators__.remove(validator)

    @timed
    def validate(self, json_data) -> Immunization:
        """Generate the Immunization model"""
        self.set_reduce_validation_code(json_data)
        self.add_custom_root_pre_validators()

        if self.add_post_validators and not self.reduce_validation_code:
            self.add_custom_root_post_validators()

        immunization = self.immunization.parse_obj(json_data)

        return immunization
