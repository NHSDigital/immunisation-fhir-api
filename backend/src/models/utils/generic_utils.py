"""Generic utilities"""

import datetime

from typing import Literal, Union, Optional


def get_contained_resource(imms: dict, resource: Literal["Patient", "Practitioner", "QuestionnaireResponse"]):
    """Extract and return the requested contained resource from the FHIR Immunization Resource JSON data"""
    return [x for x in imms.get("contained") if x.get("resourceType") == resource][0]


def get_contained_patient(imms: dict):
    """Extract and return the contained patient from the FHIR Immunization Resource JSON data"""
    return get_contained_resource(imms, "Patient")


def get_contained_practitioner(imms: dict):
    """Extract and return the contained practitioner from the FHIR Immunization Resource JSON data"""
    return get_contained_resource(imms, "Practitioner")


def get_generic_extension_value(
    json_data: dict, url: str, system: str, field_type: Literal["code", "display"]
) -> Union[str, None]:
    """Get the value of an extension field, given its url, field_type, and system"""
    value_codeable_concept = [x for x in json_data["extension"] if x.get("url") == url][0]["valueCodeableConcept"]
    value_codeable_concept_coding = value_codeable_concept["coding"]
    value = [x for x in value_codeable_concept_coding if x.get("system") == system][0][field_type]
    return value


def generate_field_location_for_extension(url: str, system: str, field_type: Literal["code", "display"]) -> str:
    """Generate the field location string for extension items"""
    return f"extension[?(@.url=='{url}')].valueCodeableConcept.coding[?(@.system=='{system}')].{field_type}"


def is_organization(x):
    """Returns boolean indicating whether the input dictionary is for an organization"""
    try:
        return x["actor"]["type"] == "Organization"
    except KeyError:
        return False


def is_actor_referencing_contained_resource(element, contained_resource_id):
    """Returns boolean indicating whether the input dictionary is for an actor which references a contained resource"""
    try:
        reference = element["actor"]["reference"]
        return reference == f"#{contained_resource_id}"
    except KeyError:
        return False


def nhs_number_mod11_check(nhs_number: str) -> bool:
    """
    Parameters:-
    nhs_number: str
        The NHS number to be checked.
    Returns:-
        True if the nhs number passes the mod 11 check, False otherwise.

    Definition of NHS number can be found at:
    https://www.datadictionary.nhs.uk/attributes/nhs_number.html
    """
    is_mod11 = False
    if nhs_number.isdigit() and len(nhs_number) == 10:
        # Create a reversed list of weighting factors
        weighting_factors = list(range(2, 11))[::-1]
        # Multiply each of the first nine digits by the weighting factor and add the results of each multiplication
        # together
        total = sum(int(digit) * weight for digit, weight in zip(nhs_number[:-1], weighting_factors))
        # Divide the total by 11 and establish the remainder and subtract the remainder from 11 to give the check digit.
        # If the result is 11 then a check digit of 0 is used. If the result is 10 then the NHS NUMBER is invalid and
        # not used.
        check_digit = 0 if (total % 11 == 0) else (11 - (total % 11))
        # Check the remainder matches the check digit. If it does not, the NHS NUMBER is invalid.
        is_mod11 = check_digit == int(nhs_number[-1])

    return is_mod11


def get_occurrence_datetime(immunization: dict) -> Optional[datetime.datetime]:
    occurrence_datetime_str: Optional[str] = immunization.get("occurrenceDateTime", None)
    if occurrence_datetime_str is None:
        return None

    return datetime.datetime.fromisoformat(occurrence_datetime_str)


def create_diagnostics():
    diagnostics = f"Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists."
    exp_error = {"diagnostics": diagnostics}
    return exp_error


def create_diagnostics_error(value):
    if value == "Both":
        diagnostics = (
            f"Validation errors: identifier[0].system and identifier[0].value doesn't match with the stored content"
        )
    else:
        diagnostics = f"Validation errors: identifier[0].{value} doesn't match with the stored content"
    exp_error = {"diagnostics": diagnostics}
    return exp_error
