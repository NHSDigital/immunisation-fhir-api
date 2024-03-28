"""Dictionary of vaccine procedure snomed codes and their mapping to vaccine type"""

from dataclasses import dataclass, field


@dataclass
class VaccineTypes:
    """Vaccine types"""

    covid_19: str = "COVID19"
    flu: str = "FLU"
    hpv: str = "HPV"
    mmr: str = "MMR"

    all: list[str] = \
        field(default_factory=lambda: [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr])


@dataclass
class Mandation:
    """Mandation types"""

    mandatory: str = "M"
    conditional_mandatory: str = "CM"
    required: str = "R"
    optional: str = "O"
    not_applicable: str = "N/A"


# TODO: Update dictionary to use correct codes and mappings once received from Imms team
# Dictionary of vaccine procedure snomed codes and their mapping to vaccine type. Any new codes
# should be added here
vaccination_procedure_snomed_codes = {
    "1324681000000101": VaccineTypes.covid_19,
    "1324691000000104": VaccineTypes.covid_19,
    "1324671000000103": VaccineTypes.covid_19,
    "1362591000000103": VaccineTypes.covid_19,
    "1363861000000103": VaccineTypes.covid_19,
    "1363791000000101": VaccineTypes.covid_19,
    "1363831000000108": VaccineTypes.covid_19,
    "822851000000102": VaccineTypes.flu,  # TODO: remove this code if necessary once full list of
    # accceptable codes is received (note that it has been copied from the sample data, to allow
    # the sample flu data to pass the validator)
    "mockFLUcode1": VaccineTypes.flu,
    "mockFLUcode2": VaccineTypes.flu,
    "mockHPVcode1": VaccineTypes.hpv,
    "mockHPVcode2": VaccineTypes.hpv,
    "mockMMRcode1": VaccineTypes.mmr,
    "mockMMRcode2": VaccineTypes.mmr,
    "mockOTHERDISEASEcode1": "OTHER_DISEASE",
    "mockMENINGITIScode1": "MEN",
}

vaccine_type_to_sample_vaccination_procedure_snomed_code = {
    VaccineTypes.covid_19: "1324681000000101",
    VaccineTypes.flu: "mockFLUcode1",
    VaccineTypes.hpv: "mockHPVcode1",
    VaccineTypes.mmr: "mockMMRcode1",
}

# Dictionary of vaccine types and their applicable mandations for each field
vaccine_type_applicable_validations = {
    "patient_identifier_value": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "patient_name_given": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "patient_name_family": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "patient_birth_date": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "patient_gender": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "patient_address_postal_code": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "occurrence_date_time": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "organization_identifier_value": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "organization_display": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "identifier_value": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "identifier_system": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "practitioner_name_given": {
        VaccineTypes.covid_19: Mandation.optional,
        VaccineTypes.flu: Mandation.optional,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "practitioner_name_family": {
        VaccineTypes.covid_19: Mandation.optional,
        VaccineTypes.flu: Mandation.optional,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "practitioner_identifier_value": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "practitioner_identifier_system": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "performer_sds_job_role": {
        VaccineTypes.covid_19: Mandation.optional,
        VaccineTypes.flu: Mandation.optional,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "recorded": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "primary_source": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "report_origin_text": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.conditional_mandatory,
        VaccineTypes.mmr: Mandation.conditional_mandatory,
    },
    "vaccination_procedure_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "vaccination_situation_code": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.conditional_mandatory,
        VaccineTypes.mmr: Mandation.conditional_mandatory,
    },
    "vaccination_situation_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "status_reason_coding_code": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.conditional_mandatory,
        VaccineTypes.mmr: Mandation.conditional_mandatory,
    },
    "status_reason_coding_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "protocol_applied_dose_number_positive_int": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "vaccine_code_coding_code": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "vaccine_code_coding_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "manufacturer_display": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "lot_number": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "expiration_date": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "site_coding_code": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "site_coding_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "route_coding_code": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "route_coding_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "dose_quantity_value": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "dose_quantity_code": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "dose_quantity_unit": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "reason_code_coding_code": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "reason_code_coding_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "nhs_number_verification_status_code": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "nhs_number_verification_status_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.required,
        VaccineTypes.mmr: Mandation.required,
    },
    "organization_identifier_system": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "local_patient_value": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "local_patient_system": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.mandatory,
    },
    "consent_code": {
        VaccineTypes.covid_19: Mandation.conditional_mandatory,
        VaccineTypes.flu: Mandation.conditional_mandatory,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "consent_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "care_setting_code": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "care_setting_display": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.required,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
    "ip_address": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.not_applicable,
        VaccineTypes.hpv: Mandation.not_applicable,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "user_id": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.not_applicable,
        VaccineTypes.hpv: Mandation.not_applicable,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "user_name": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.not_applicable,
        VaccineTypes.hpv: Mandation.not_applicable,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "user_email": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.not_applicable,
        VaccineTypes.hpv: Mandation.not_applicable,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "submitted_time_stamp": {
        VaccineTypes.covid_19: Mandation.required,
        VaccineTypes.flu: Mandation.not_applicable,
        VaccineTypes.hpv: Mandation.not_applicable,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "location_identifier_value": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "location_identifier_system": {
        VaccineTypes.covid_19: Mandation.mandatory,
        VaccineTypes.flu: Mandation.mandatory,
        VaccineTypes.hpv: Mandation.mandatory,
        VaccineTypes.mmr: Mandation.not_applicable,
    },
    "reduce_validation_reason": {
        VaccineTypes.covid_19: Mandation.optional,
        VaccineTypes.flu: Mandation.optional,
        VaccineTypes.hpv: Mandation.optional,
        VaccineTypes.mmr: Mandation.optional,
    },
}
