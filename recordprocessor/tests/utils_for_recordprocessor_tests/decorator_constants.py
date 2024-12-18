"""Constants for use when testing decorators"""

from decimal import Decimal
from src.constants import Urls
from src.mappings import Vaccine
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import TargetDiseaseElements

VALID_NHS_NUMBER = "1345678940"
ADDRESS_UNKNOWN_POSTCODE = "ZZ99 3WZ"

RSV_TARGET_DISEASE_ELEMENT = getattr(TargetDiseaseElements, Vaccine.RSV.value)


class ExtensionItems:
    """Class containing standard extension items"""

    vaccination_procedure_url = Urls.VACCINATION_PROCEDURE
    snomed_url = Urls.SNOMED

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


class AllHeaders:
    """Class containing all headers for each decorator"""

    immunization = {
        "INDICATION_CODE": "INDICATION_CODE",
        "RECORDED_DATE": "20000101",
        "UNIQUE_ID": "UNIQUE_ID_123",
        "UNIQUE_ID_URI": "unique_id_uri",
    }

    patient = {
        "PERSON_SURNAME": "surname",
        "PERSON_FORENAME": "forename",
        "PERSON_GENDER_CODE": "1",
        "PERSON_DOB": "20000101",
        "PERSON_POSTCODE": "ZZ99 3WZ",
        "NHS_NUMBER": "1345678940",
    }

    vaccine = {
        "VACCINE_PRODUCT_CODE": "a_vacc_code",
        "VACCINE_PRODUCT_TERM": "a_vacc_term",
        "VACCINE_MANUFACTURER": "a_manufacturer",
        "EXPIRY_DATE": "20000101",
        "BATCH_NUMBER": "a_batch_number",
    }

    vaccination = {
        "VACCINATION_PROCEDURE_CODE": "a_vaccination_procedure_code",
        "VACCINATION_PROCEDURE_TERM": "a_vaccination_procedure_term",
        "DATE_AND_TIME": "20000101T11111101",
        "PRIMARY_SOURCE": "True",
        "SITE_OF_VACCINATION_CODE": "a_vacc_site_code",
        "SITE_OF_VACCINATION_TERM": "a_vacc_site_term",
        "ROUTE_OF_VACCINATION_CODE": "a_vacc_route_code",
        "ROUTE_OF_VACCINATION_TERM": "a_vacc_route_term",
        "DOSE_AMOUNT": "0.5",
        "DOSE_UNIT_TERM": "a_dose_unit_term",
        "DOSE_UNIT_CODE": "a_dose_unit_code",
        "DOSE_SEQUENCE": "1",
    }

    performer = {
        "SITE_CODE_TYPE_URI": "a_site_code_type_uri",
        "SITE_CODE": "a_site_code",
        "PERFORMING_PROFESSIONAL_SURNAME": "a_prof_surname",
        "PERFORMING_PROFESSIONAL_FORENAME": "a_prof_forename",
        "LOCATION_CODE": "a_location_code",
        "LOCATION_CODE_TYPE_URI": "a_location_code_uri",
    }


class AllHeadersExpectedOutput:
    """
    Class containing the expected output for each decorator when given all headers (with values as defined in the
    AllHeaders class)
    """

    immunization = {
        "resourceType": "Immunization",
        "status": "completed",
        "protocolApplied": [{"targetDisease": RSV_TARGET_DISEASE_ELEMENT}],
        "reasonCode": [{"coding": [{"system": Urls.SNOMED, "code": "INDICATION_CODE"}]}],
        "recorded": "2000-01-01",
        "identifier": [{"system": "unique_id_uri", "value": "UNIQUE_ID_123"}],
    }

    patient = {
        "resourceType": "Immunization",
        "status": "completed",
        "protocolApplied": [{"targetDisease": RSV_TARGET_DISEASE_ELEMENT}],
        "contained": [
            {
                "resourceType": "Patient",
                "id": "Patient1",
                "identifier": [{"system": Urls.NHS_NUMBER, "value": VALID_NHS_NUMBER}],
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
        "status": "completed",
        "protocolApplied": [{"targetDisease": RSV_TARGET_DISEASE_ELEMENT}],
        "vaccineCode": {"coding": [{"system": Urls.SNOMED, "code": "a_vacc_code", "display": "a_vacc_term"}]},
        "manufacturer": {"display": "a_manufacturer"},
        "lotNumber": "a_batch_number",
        "expirationDate": "2000-01-01",
    }

    vaccination = {
        "resourceType": "Immunization",
        "status": "completed",
        "protocolApplied": [{"targetDisease": RSV_TARGET_DISEASE_ELEMENT, "doseNumberPositiveInt": 1}],
        "extension": [ExtensionItems.vaccination_procedure],
        "occurrenceDateTime": "2000-01-01T11:11:11+01:00",
        "primarySource": True,
        "site": {"coding": [{"system": Urls.SNOMED, "code": "a_vacc_site_code", "display": "a_vacc_site_term"}]},
        "route": {"coding": [{"system": Urls.SNOMED, "code": "a_vacc_route_code", "display": "a_vacc_route_term"}]},
        "doseQuantity": {
            "value": Decimal(0.5),
            "unit": "a_dose_unit_term",
            "system": Urls.SNOMED,
            "code": "a_dose_unit_code",
        },
    }

    performer = {
        "resourceType": "Immunization",
        "status": "completed",
        "protocolApplied": [{"targetDisease": RSV_TARGET_DISEASE_ELEMENT}],
        "contained": [
            {
                "resourceType": "Practitioner",
                "id": "Practitioner1",
                "name": [{"family": "a_prof_surname", "given": ["a_prof_forename"]}],
            }
        ],
        "performer": [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "a_site_code_type_uri", "value": "a_site_code"},
                }
            },
            {"actor": {"reference": "#Practitioner1"}},
        ],
        "location": {"identifier": {"value": "a_location_code", "system": "a_location_code_uri"}},
    }
