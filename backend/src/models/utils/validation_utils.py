"""Utils for backend folder"""

from typing import Union
from mappings import vaccine_type_mappings
import json
from .generic_utils import create_diagnostics_error


def disease_codes_to_vaccine_type(disease_codes_input: list) -> Union[str, None]:
    """
    Takes a list of disease codes and returns the corresponding vaccine type if found,
    otherwise raises a value error
    """
    try:
        return next(
            vaccine_type
            for disease_codes, vaccine_type in vaccine_type_mappings
            if sorted(disease_codes_input) == disease_codes
        )
    except Exception as e:
        raise ValueError(f"{disease_codes_input} is not a valid combination of disease codes for this service") from e


def get_vaccine_type(immunization: dict):
    """
    Take a FHIR immunization resource and returns the vaccine type based on the combination of target diseases.
    If combination of disease types does not map to a valid vaccine type, a value error is raised
    """
    try:
        target_diseases = []
        target_disease_list = immunization["protocolApplied"][0]["targetDisease"]
        for element in target_disease_list:
            code = [x.get("code") for x in element["coding"] if x.get("system") == "http://snomed.info/sct"][0]
            target_diseases.append(code)
    except (KeyError, IndexError, AttributeError) as error:
        raise ValueError("No target disease codes found") from error
    return disease_codes_to_vaccine_type(target_diseases)


def has_valid_vaccine_type(immunization: dict):
    """Returns vaccine type if combination of disease codes is valid, otherwise returns False"""
    try:
        return get_vaccine_type(immunization)
    except ValueError:
        return False
    
def check_identifier_system_value(response, imms, app_id):
    """Returns diagnostics if identifier's system and value does not match with the stored content """
    
    app_id_response = response['Item'].get('appId', None)
    if app_id != app_id_response:
        value = "Unauthorized"
        diagnostics_error = create_diagnostics_error(value)
        return diagnostics_error 

    if imms is not None:
        identifier_system_request = imms["identifier"][0]["system"]
        identifier_value_request = imms["identifier"][0]["value"]
        resource_str = response['Item']['Resource']
        resource = json.loads(resource_str)
        identifier_system_response = resource["identifier"][0]["system"]
        identifier_value_response = resource["identifier"][0]["value"]

        if identifier_system_request != identifier_system_response and identifier_value_request != identifier_value_response:
            value = "Both"
            diagnostics_error = create_diagnostics_error(value)
            return diagnostics_error 
        if identifier_system_request != identifier_system_response:
            value = "system"
            diagnostics_error = create_diagnostics_error(value)
            return diagnostics_error 
        if identifier_value_request != identifier_value_response:
            value = "value"
            diagnostics_error = create_diagnostics_error(value)
            return diagnostics_error 
    else:
        None    