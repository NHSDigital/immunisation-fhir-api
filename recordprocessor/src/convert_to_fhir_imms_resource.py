""" "Decorators to add the relevant fields to the FHIR immunization resource from the batch stream"""

from typing import List, Callable, Dict
from utils_for_fhir_conversion import _is_not_empty, Generate, Add, Convert
from mappings import map_target_disease
from constants import Urls


ImmunizationDecorator = Callable[[Dict, Dict[str, str]], None]
"""
A decorator function (Callable) takes the current immunization resource and adds appropriate fields to it.
NOTE: NO VALIDATION should be performed. Validation is left to the Imms API validator.
NOTE: An overarching data rule is that where data is not present the field should not be added to the FHIR Immunization
resource. Therefore before adding an element it is necessary to check that at least one of its values is non-empty.
"""


def _decorate_immunization(imms: dict, row: Dict[str, str]) -> None:
    """Adds the reasonCode, recorded and identifier elements (where non-empty data is provided)"""
    indication_code = row.get("INDICATION_CODE")
    reason_code_value = [{"coding": [{"system": Urls.SNOMED, "code": indication_code}]}]
    Add.custom_item(imms, "reasonCode", [indication_code], reason_code_value)

    Add.item(imms, "recorded", row.get("RECORDED_DATE"), Convert.date)

    Add.list_of_dict(imms, "identifier", {"value": row.get("UNIQUE_ID"), "system": row.get("UNIQUE_ID_URI")})


def _decorate_patient(imms: dict, row: Dict[str, str]) -> None:
    """Creates the patient resource and appends it the to 'contained' list"""
    patient_values = [
        person_surname := row.get("PERSON_SURNAME"),
        person_forename := row.get("PERSON_FORENAME"),
        person_gender_code := row.get("PERSON_GENDER_CODE"),
        person_dob := row.get("PERSON_DOB"),
        person_postcode := row.get("PERSON_POSTCODE"),
        nhs_number := row.get("NHS_NUMBER"),
    ]

    # Add patient if there is at least one non-empty patient value
    if any(_is_not_empty(value) for value in patient_values):

        # Set up patient
        internal_patient_id = "Patient1"
        imms["patient"] = {"reference": f"#{internal_patient_id}"}
        patient = {"id": internal_patient_id, "resourceType": "Patient"}

        Add.item(patient, "birthDate", person_dob, Convert.date)

        Add.item(patient, "gender", person_gender_code, Convert.gender_code)

        Add.list_of_dict(patient, "address", {"postalCode": person_postcode})

        Add.custom_item(patient, "identifier", nhs_number, [{"system": Urls.NHS_NUMBER, "value": nhs_number}])

        # Add patient name if there is at least one non-empty patient name value
        if any(_is_not_empty(value) for value in [person_surname, person_forename]):
            patient["name"] = [{}]
            Add.item(patient["name"][0], "family", person_surname)
            Add.custom_item(patient["name"][0], "given", [person_forename], [person_forename])

        # Add practitioner to contained list if it exists, else create a contained list and add it to imms
        imms.setdefault("contained", []).append(patient)


def _decorate_vaccine(imms: dict, row: Dict[str, str]) -> None:
    """Adds fields relating to the physical product"""

    vax_prod_code = row.get("VACCINE_PRODUCT_CODE")
    vax_prod_term = row.get("VACCINE_PRODUCT_TERM")
    vax_prod_system = Urls.SNOMED
    # vaccineCode is a mandatory FHIR field. If no values are supplied a default null flavour code of 'NAVU' is used.
    if not (vax_prod_code or vax_prod_term):
        vax_prod_code, vax_prod_term, vax_prod_system = "NAVU", "Not available", Urls.NULL_FLAVOUR_CODES
    imms["vaccineCode"] = {
        "coding": [Generate.dictionary({"system": vax_prod_system, "code": vax_prod_code, "display": vax_prod_term})]
    }

    Add.dictionary(imms, "manufacturer", {"display": row.get("VACCINE_MANUFACTURER")})

    Add.item(imms, "expirationDate", row.get("EXPIRY_DATE"), Convert.date)

    Add.item(imms, "lotNumber", row.get("BATCH_NUMBER"))


def _decorate_vaccination(imms: dict, row: Dict[str, str]) -> None:
    """Adds fields relating to the administration of the vaccine"""
    vaccination_extension_values = [
        vaccination_procedure_code := row.get("VACCINATION_PROCEDURE_CODE"),
        vaccination_procedure_term := row.get("VACCINATION_PROCEDURE_TERM"),
    ]

    # Add extension item if at least one extension item value is non-empty
    if any(_is_not_empty(value) for value in vaccination_extension_values):
        imms["extension"] = []

        imms["extension"].append(
            Generate.extension_item(
                url=Urls.VACCINATION_PROCEDURE,
                system=Urls.SNOMED,
                code=vaccination_procedure_code,
                display=vaccination_procedure_term,
            )
        )

    Add.item(imms, "occurrenceDateTime", row.get("DATE_AND_TIME"), Convert.date_time)

    Add.item(imms, "primarySource", row.get("PRIMARY_SOURCE"), Convert.boolean)

    Add.snomed(imms, "site", row.get("SITE_OF_VACCINATION_CODE"), row.get("SITE_OF_VACCINATION_TERM"))

    Add.snomed(imms, "route", row.get("ROUTE_OF_VACCINATION_CODE"), row.get("ROUTE_OF_VACCINATION_TERM"))

    dose_quantity_values = [
        dose_amount := row.get("DOSE_AMOUNT"),
        dose_unit_term := row.get("DOSE_UNIT_TERM"),
        dose_unit_code := row.get("DOSE_UNIT_CODE"),
    ]
    dose_quantity_dict = {
        "value": Convert.integer_or_decimal(dose_amount),
        "unit": dose_unit_term,
        # Only include system if dose unit code is  non-empty
        **({"system": Urls.SNOMED} if _is_not_empty(dose_unit_code) else {}),
        "code": dose_unit_code,
    }
    Add.custom_item(imms, "doseQuantity", dose_quantity_values, Generate.dictionary(dose_quantity_dict))

    # If DOSE_SEQUENCE is empty, default FHIR "doseNumberString" to "Dose sequence not recorded",
    # otherwise assume the sender's intentiion is to supply a positive integer
    if _is_not_empty(dose_sequence := row.get("DOSE_SEQUENCE")):
        Add.item(imms["protocolApplied"][0], "doseNumberPositiveInt", dose_sequence, Convert.integer)
    else:
        Add.item(imms["protocolApplied"][0], "doseNumberString", "Dose sequence not recorded")


def _decorate_performer(imms: dict, row: Dict[str, str]) -> None:
    """
    Adds the performer field, including organization, and where relevant creates the practitioner resource
    and adds it to the 'contained' list
    """
    organization_values = [
        site_code_type_uri := row.get("SITE_CODE_TYPE_URI"),
        site_code := row.get("SITE_CODE"),
    ]
    practitioner_values = [
        performing_prof_surname := row.get("PERFORMING_PROFESSIONAL_SURNAME"),
        performing_prof_forename := row.get("PERFORMING_PROFESSIONAL_FORENAME"),
    ]
    peformer_values = organization_values + practitioner_values

    # Add performer if there is at least one non-empty performer value
    if any(_is_not_empty(value) for value in peformer_values):
        imms["performer"] = []

        # Add organization if there is at least one non-empty organization value
        if any(_is_not_empty(value) for value in organization_values):
            organization = {"actor": {"type": "Organization"}}

            Add.dictionary(organization["actor"], "identifier", {"system": site_code_type_uri, "value": site_code})

            imms["performer"].append(organization)

        # Add practitioner if there is at least one practitioner value
        if any(_is_not_empty(value) for value in practitioner_values):

            # Set up the practitioner
            internal_practitioner_id = "Practitioner1"
            practitioner = {"resourceType": "Practitioner", "id": internal_practitioner_id}
            imms["performer"].append({"actor": {"reference": f"#{internal_practitioner_id}"}})

            # Add practitioner name if there is at least one non-empty practitioner name value
            if any(_is_not_empty(value) for value in [performing_prof_surname, performing_prof_forename]):
                practitioner["name"] = [{}]
                Add.item(practitioner["name"][0], "family", performing_prof_surname)
                Add.custom_item(
                    practitioner["name"][0], "given", [performing_prof_forename], [performing_prof_forename]
                )

            # Add practitioner to contained list if it exists, else create a contained list and add it to imms
            imms.setdefault("contained", []).append(practitioner)

    Add.custom_item(
        imms,
        "location",
        [location_code := row.get("LOCATION_CODE"), location_code_type_uri := row.get("LOCATION_CODE_TYPE_URI")],
        {"identifier": Generate.dictionary({"value": location_code, "system": location_code_type_uri})},
    )


all_decorators: List[ImmunizationDecorator] = [
    _decorate_immunization,
    _decorate_patient,
    _decorate_vaccine,
    _decorate_vaccination,
    _decorate_performer,
]


def convert_to_fhir_imms_resource(row: dict, target_disease: list) -> dict:
    """Converts a row of data to a FHIR Immunization Resource"""
    # Prepare the imms_resource. Note that all data sent via this service is assumed to be for completed vaccinations.
    imms_resource = {
        "resourceType": "Immunization",
        "status": "completed",
        "protocolApplied": [{"targetDisease": target_disease}]
    }

    # Apply all decorators to add the relevant fields to the imms_resource
    for decorator in all_decorators:
        decorator(imms_resource, row)

    return imms_resource
