"""Constants for use when testing decorators"""

from collections import OrderedDict
from decimal import Decimal

from constants import VALID_NHS_NUMBER, ADDRESS_UNKNOWN_POSTCODE


class ExtensionItems:
    """Class containing standard extension items"""

    vaccination_procedure_url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    vaccination_situation_url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation"
    snomed_url = "http://snomed.info/sct"
    nhs_number_verification_url = (
        "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
    )
    nhs_number_verification_system_url = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"

    vaccination_procedure = {
        "url": vaccination_procedure_url,
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": snomed_url,
                    "code": "a_vaccination_procedure_code",
                    "display": "a_vaccination_procedure_term",
                }
            ]
        },
    }

    vaccination_situation = {
        "url": vaccination_situation_url,
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": snomed_url,
                    "code": "a_vaccination_situation_code",
                    "display": "a_vaccination_situation_term",
                }
            ]
        },
    }

    nhs_number_status = {
        "url": nhs_number_verification_url,
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": nhs_number_verification_system_url,
                    "code": "an_nhs_status_code",
                    "display": "an_nhs_status_description",
                }
            ]
        },
    }


class AllHeaders:
    """Class containing all headers for each decorator"""

    immunization_completed = OrderedDict(
        [
            ("not_given", "false"),
            ("action_flag", "new"),
            ("indication_code", "INDICATION_CODE"),
            ("indication_term", "indication term"),
            ("recorded_date", "20000101"),
            ("unique_id", "UNIQUE_ID_123"),
            ("unique_id_uri", "unique_id_uri"),
        ]
    )

    immunization_not_done = OrderedDict(
        [
            ("not_given", "true"),
            ("action_flag", "new"),
            ("reason_not_given_code", "REASON_NOT_GIVEN_CODE"),
            ("reason_not_given_term", "reason not given term"),
            ("recorded_date", "20000101"),
            ("unique_id", "UNIQUE_ID_123"),
            ("unique_id_uri", "unique_id_uri"),
        ]
    )

    patient = OrderedDict(
        [
            ("person_surname", "surname"),
            ("person_forename", "forename"),
            ("person_gender_code", "1"),
            ("person_dob", "20000101"),
            ("person_postcode", ADDRESS_UNKNOWN_POSTCODE),
            ("nhs_number", VALID_NHS_NUMBER),
            ("nhs_number_status_indicator_code", "an_nhs_status_code"),
            ("nhs_number_status_indicator_description", "an_nhs_status_description"),
        ]
    )

    vaccine = OrderedDict(
        [
            ("vaccine_product_code", "a_vacc_code"),
            ("vaccine_product_term", "a_vacc_term"),
            ("vaccine_manufacturer", "a_manufacturer"),
            ("expiry_date", "20000101"),
            ("batch_number", "a_batch_number"),
        ]
    )

    vaccination = OrderedDict(
        [
            ("vaccination_procedure_code", "a_vaccination_procedure_code"),
            ("vaccination_procedure_term", "a_vaccination_procedure_term"),
            ("vaccination_situation_code", "a_vaccination_situation_code"),
            ("vaccination_situation_term", "a_vaccination_situation_term"),
            ("date_and_time", "20000101T11111101"),
            ("primary_source", "True"),
            ("report_origin", "a_report_origin"),
            ("site_of_vaccination_code", "a_vacc_site_code"),
            ("site_of_vaccination_term", "a_vacc_site_term"),
            ("route_of_vaccination_code", "a_vacc_route_code"),
            ("route_of_vaccination_term", "a_vacc_route_term"),
            ("dose_amount", "0.5"),
            ("dose_unit_term", "a_dose_unit_term"),
            ("dose_unit_code", "a_dose_unit_code"),
            ("dose_sequence", "3"),
        ]
    )

    performer = OrderedDict(
        [
            ("site_code_type_uri", "a_site_code_type_uri"),
            ("site_code", "a_site_code"),
            ("site_name", "a_site_name"),
            ("performing_professional_body_reg_uri", "a_prof_body_uri"),
            ("performing_professional_body_reg_code", "a_prof_body_code"),
            ("performing_professional_surname", "a_prof_surname"),
            ("performing_professional_forename", "a_prof_forename"),
            ("location_code", "a_location_code"),
            ("location_code_type_uri", "a_location_code_uri"),
        ]
    )

    questionnaire = OrderedDict(
        [
            ("consent_for_treatment_code", "a_consent_code"),
            ("consent_for_treatment_description", "a_consent_description"),
            ("care_setting_type_code", "a_care_setting_code"),
            ("care_setting_type_description", "a_care_setting_description"),
            ("reduce_validation_code", "false"),
            ("reduce_validation_reason", "a_reduce_validation_reason"),
            ("local_patient_uri", "a_local_patient_uri"),
            ("local_patient_id", "a_local_patient_id"),
            ("ip_address", "an_ip_address"),
            ("user_id", "a_user_id"),
            ("user_name", "a_user_name"),
            ("user_email", "a_user_email"),
            ("submitted_timestamp", "20000101T121212"),
            ("sds_job_role_name", "an_sds_job_role_name"),
        ]
    )


class AllHeadersExpectedOutput:
    """
    Class containing the expected output for each decorator when given all headers (with values as defined in the
    AllHeaders class)
    """

    immunization_completed = {
        "resourceType": "Immunization",
        "contained": [],
        "status": "completed",
        "reasonCode": [{"coding": [{"code": "INDICATION_CODE", "display": "indication term"}]}],
        "recorded": "2000-01-01",
        "identifier": [{"system": "unique_id_uri", "value": "UNIQUE_ID_123"}],
    }

    immunization_not_done = {
        "resourceType": "Immunization",
        "contained": [],
        "status": "not-done",
        "statusReason": {"coding": [{"code": "REASON_NOT_GIVEN_CODE", "display": "reason not given term"}]},
        "recorded": "2000-01-01",
        "identifier": [{"system": "unique_id_uri", "value": "UNIQUE_ID_123"}],
    }

    patient = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Patient",
                "id": "Patient1",
                "identifier": [
                    {
                        "extension": [ExtensionItems.nhs_number_status],
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": VALID_NHS_NUMBER,
                    }
                ],
                "name": [{"family": "surname", "given": ["forename"]}],
                "gender": "male",
                "birthDate": "2000-01-01",
                "address": [{"postalCode": ADDRESS_UNKNOWN_POSTCODE}],
            },
        ],
        "patient": {"reference": "#Patient1"},
    }

    vaccine = {
        "resourceType": "Immunization",
        "contained": [],
        "vaccineCode": {
            "coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_code", "display": "a_vacc_term"}]
        },
        "manufacturer": {"display": "a_manufacturer"},
        "lotNumber": "a_batch_number",
        "expirationDate": "2000-01-01",
    }

    vaccination = {
        "resourceType": "Immunization",
        "contained": [],
        "extension": [ExtensionItems.vaccination_procedure, ExtensionItems.vaccination_situation],
        "occurrenceDateTime": "2000-01-01T11:11:11+01:00",
        "primarySource": True,
        "reportOrigin": {"text": "a_report_origin"},
        "site": {
            "coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_site_code", "display": "a_vacc_site_term"}]
        },
        "route": {
            "coding": [
                {"system": "http://snomed.info/sct", "code": "a_vacc_route_code", "display": "a_vacc_route_term"}
            ]
        },
        "doseQuantity": {
            "value": Decimal(0.5),
            "unit": "a_dose_unit_term",
            "system": "http://unitsofmeasure.org",
            "code": "a_dose_unit_code",
        },
        "protocolApplied": [{"doseNumberPositiveInt": 3}],
    }

    performer = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Practitioner",
                "id": "Practitioner1",
                "identifier": [{"system": "a_prof_body_uri", "value": "a_prof_body_code"}],
                "name": [{"family": "a_prof_surname", "given": ["a_prof_forename"]}],
            }
        ],
        "performer": [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "a_site_code_type_uri", "value": "a_site_code"},
                    "display": "a_site_name",
                }
            },
            {"actor": {"reference": "#Practitioner1"}},
        ],
        "location": {
            "type": "Location",
            "identifier": {"value": "a_location_code", "system": "a_location_code_uri"},
        },
    }

    questionnaire = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "QuestionnaireResponse",
                "id": "QR1",
                "status": "completed",
                "item": [
                    {
                        "linkId": "Consent",
                        "answer": [{"valueCoding": {"code": "a_consent_code", "display": "a_consent_description"}}],
                    },
                    {
                        "linkId": "CareSetting",
                        "answer": [
                            {
                                "valueCoding": {
                                    "code": "a_care_setting_code",
                                    "display": "a_care_setting_description",
                                }
                            }
                        ],
                    },
                    {"linkId": "ReduceValidation", "answer": [{"valueBoolean": False}]},
                    {
                        "linkId": "LocalPatient",
                        "answer": [
                            {
                                "valueReference": {
                                    "identifier": {"system": "a_local_patient_uri", "value": "a_local_patient_id"}
                                }
                            }
                        ],
                    },
                    {"linkId": "SubmittedTimeStamp", "answer": [{"valueDateTime": "2000-01-01T12:12:12+00:00"}]},
                    {"linkId": "IpAddress", "answer": [{"valueString": "an_ip_address"}]},
                    {"linkId": "UserId", "answer": [{"valueString": "a_user_id"}]},
                    {"linkId": "UserName", "answer": [{"valueString": "a_user_name"}]},
                    {"linkId": "UserEmail", "answer": [{"valueString": "a_user_email"}]},
                    {"linkId": "PerformerSDSJobRole", "answer": [{"valueString": "an_sds_job_role_name"}]},
                    {"linkId": "ReduceValidationReason", "answer": [{"valueString": "a_reduce_validation_reason"}]},
                ],
            }
        ],
    }
