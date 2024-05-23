"""Generic utilities for models"""

import datetime

from typing import Literal, Union, Optional, Any


def get_contained_resource_from_model(
    values: dict,
    resource: Literal["Patient", "Practitioner", "QuestionnaireResponse"],
):
    """Extract and return the requested contained resource from values model"""
    return [x for x in values.contained if x.resource_type == resource][0]


def get_generic_questionnaire_response_value(
    json_data: dict,
    link_id: str,
    answer_type: Literal["valueBoolean", "valueString", "valueDateTime", "valueCoding"],
    field_type: Optional[Literal["code", "display", "system"]] = None,
) -> Any:
    """
    Get the value of a QuestionnaireResponse field, given its linkId

    Parameters:-
    json_data: dict
        The json data to be validated
    answer_type: Literal["valueBoolean", "valueString", "valueDateTime", "valueCoding"]
        The answer type to be validated
    link_id: str
        The linkId of the field to be validated
    value_coding_field_type: Optional[Literal["code", "display", "system"]]
        The value coding field type to be validated, must be provided for valueCoding fields
    """

    questionnaire_reponse = [x for x in json_data["contained"] if x.get("resourceType") == "QuestionnaireResponse"][0]

    item = [x for x in questionnaire_reponse["item"] if x.get("linkId") == link_id][0]

    if answer_type == "valueCoding":
        value = item["answer"][0][answer_type][field_type]

    if answer_type == "valueReference":
        value = item["answer"][0][answer_type]["identifier"][field_type]

    if answer_type in ("valueBoolean", "valueString", "valueDateTime"):
        value = item["answer"][0][answer_type]

    return value


def get_generic_questionnaire_response_value_from_model(
    values: dict,
    link_id: str,
    answer_type: Literal["valueBoolean", "valueString", "valueDateTime", "valueCoding"],
    field_type: Optional[Literal["code", "display", "system"]] = None,
) -> Any:
    """
    Get the value of a QuestionnaireResponse field, given its linkId

    Parameters:-
    values: dict
        The model containing the values
    answer_type: Literal["valueBoolean", "valueString", "valueDateTime", "valueCoding"]
        The answer type to be validated
    link_id: str
        The linkId of the field to be validated
    value_coding_field_type: Optional[Literal["code", "display", "system"]]
        The value coding field type to be validated, must be provided for valueCoding fields
    """
    questionnaire_reponse = get_contained_resource_from_model(values, "QuestionnaireResponse")

    item = [x for x in questionnaire_reponse.item if x.linkId == link_id][0]

    if answer_type == "valueCoding":
        value = getattr(item.answer[0].valueCoding, field_type)

    if answer_type == "valueReference":
        value = getattr(item.answer[0].valueReference.identifier, field_type)

    if answer_type in ("valueBoolean", "valueString", "valueDateTime"):
        value = getattr(item.answer[0], answer_type)

    return value


def get_generic_extension_value(
    json_data: dict,
    url: str,
    system: str,
    field_type: Literal["code", "display"],
) -> Union[str, None]:
    """
    Get the value of an extension field, given its url, field_type, and system
    """
    value_codeable_concept_coding = [x for x in json_data["extension"] if x.get("url") == url][0][
        "valueCodeableConcept"
    ]["coding"]

    value = [x for x in value_codeable_concept_coding if x.get("system") == system][0][field_type]

    return value


def get_generic_extension_value_from_model(
    values: dict,
    url: str,
    system: str,
    field_type: Literal["code", "display"],
) -> Union[str, None]:
    """
    Get the value of an extension field, given its url, field_type, and system
    """
    value_codeable_concept_coding = [x for x in values.extension if x.url == url][0].valueCodeableConcept.coding

    value = getattr(
        [x for x in value_codeable_concept_coding if x.system == system][0],
        field_type,
        None,
    )

    return value


def generate_field_location_for_questionnaire_response(
    link_id: str,
    answer_type: str,
    field_type: Literal["code", "display", "system"] = None,
) -> str:
    """Generate the field location string for questionnaire response items"""
    location = "contained[?(@.resourceType=='QuestionnaireResponse')]" + f".item[?(@.linkId=='{link_id}')].answer[0]"
    if answer_type == "valueCoding":
        return f"{location}.{answer_type}.{field_type}"
    if answer_type == "valueReference":
        return f"{location}.{answer_type}.identifier.{field_type}"
    if answer_type in ("valueBoolean", "valueString", "valueDateTime"):
        return f"{location}.{answer_type}"


def generate_field_location_for_extension(url: str, system: str, field_type: Literal["code", "display"]) -> str:
    """Generate the field location string for extension items"""
    return f"extension[?(@.url=='{url}')].valueCodeableConcept." + f"coding[?(@.system=='{system}')].{field_type}"


def get_deep_attr(obj, attrs):
    for attr in attrs.split("."):
        obj = getattr(obj, attr)
    return obj


def is_organization(x):
    try:
        return x.actor.type == "Organization"
    except (AttributeError, TypeError):
        return False


def get_nhs_number_verification_status_code(imms: dict) -> Union[str, None]:
    """Get the NHS number verification status code from the contained Patient resource"""
    try:
        extension = next(
            x
            for x in get_contained_resource_from_model(imms, "Patient").identifier
            if x.system == "https://fhir.nhs.uk/Id/nhs-number"
        ).extension

        value_codeable_concept_coding = next(
            x
            for x in extension
            if x.url == "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
        ).valueCodeableConcept.coding

        verification_status_code = next(
            x
            for x in value_codeable_concept_coding
            if x.system == "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
        ).code
    except (StopIteration, KeyError, IndexError):
        verification_status_code = None

    return verification_status_code


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


def get_target_disease_codes_from_model(immunization: dict):
    """Take a FHIR immunization resource model and returns a list of target disease codes"""
    target_diseases = []
    target_disease_list = immunization.protocolApplied[0].targetDisease
    for element in target_disease_list:
        code = [x.code for x in element.coding if x.system == "http://snomed.info/sct"][0]
        if code is not None:
            target_diseases.append(code)
    return target_diseases


def get_occurrence_datetime(immunization: dict) -> Optional[datetime.datetime]:
    occurrence_datetime_str: Optional[str] = immunization.get("occurrenceDateTime", None)
    if occurrence_datetime_str is None:
        return None

    return datetime.datetime.fromisoformat(occurrence_datetime_str)

def create_diagnostics():
                diagnostics=f"Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists."
                exp_error = {
                             "diagnostics": diagnostics
                            }
                return (exp_error)
