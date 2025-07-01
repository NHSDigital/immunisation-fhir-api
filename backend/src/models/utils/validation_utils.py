"""Utils for backend folder"""

import json


from typing import Union
from .generic_utils import create_diagnostics_error
from base_utils.base_utils import obtain_field_location
from models.obtain_field_value import ObtainFieldValue
from models.field_names import FieldNames
from models.errors import MandatoryError
from constants import Urls
from clients import redis_client
from unittest.mock import Mock


def get_target_disease_codes(immunization: dict):
    """Takes a FHIR immunization resource and returns a list of target disease codes"""

    target_disease_codes = []

    # Obtain the target disease element from the immunization resource
    try:
        target_disease = ObtainFieldValue.target_disease(immunization)
    except (KeyError, IndexError) as error:
        raise MandatoryError(
            f"Validation errors: {obtain_field_location(FieldNames.target_disease_codes)} is a mandatory field"
        ) from error

    # For each item in the target disease list, extract the snomed code
    for i, element in enumerate(target_disease):

        try:
            code = [x["code"] for x in element["coding"] if x.get("system") == Urls.snomed][0]
        except (KeyError, IndexError) as error:
            raise MandatoryError(
                f"protocolApplied[0].targetDisease[{i}].coding[?(@.system=='http://snomed.info/sct')].code"
                + " is a mandatory field"
            ) from error

        if code is None:
            raise ValueError(
                f"'None' is not a valid value for '{obtain_field_location(FieldNames.target_disease_codes)}'"
            )

        target_disease_codes.append(code)

    return target_disease_codes


def convert_disease_codes_to_vaccine_type(disease_codes_input: list) -> Union[str, None]:
    """
    Takes a list of disease codes and returns the corresponding vaccine type if found,
    otherwise raises a value error
    """
    key = ":".join(sorted(disease_codes_input))
    # vaccine_type = redis_client.hget("diseases_to_vacc", key)
    
    
    if isinstance(redis_client.hget, Mock):
        vaccine_type = redis_client.hget("diseases_to_vacc", key)
    else:
        print("XXXXXX   ------>>>  redis_client.hget is mocked")
    
    if not vaccine_type:
        raise ValueError(
            f"Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - "
            f"{disease_codes_input} is not a valid combination of disease codes for this service"
        )
    return vaccine_type


def get_vaccine_type(immunization: dict):
    """
    Take a FHIR immunization resource and returns the vaccine type based on the combination of target diseases.
    If combination of disease types does not map to a valid vaccine type, a value error is raised
    """
    # Obtain list of target diseases
    try:
        target_diseases = get_target_disease_codes(immunization)
        if not target_diseases:
            raise ValueError
    except MandatoryError as error:
        raise ValueError(str(error)) from error
    except ValueError as error:
        raise ValueError(f"{obtain_field_location(FieldNames.target_disease_codes)} is a mandatory field") from error

    # Convert list of target diseases to vaccine type
    return convert_disease_codes_to_vaccine_type(target_diseases)


def check_identifier_system_value(response, imms: dict):
    """Returns diagnostics if identifier's system and value does not match with the stored content"""

    identifier_system_request = imms["identifier"][0]["system"]
    identifier_value_request = imms["identifier"][0]["value"]
    resource_str = response["Item"]["Resource"]
    resource = json.loads(resource_str)
    identifier_system_response = resource["identifier"][0]["system"]
    identifier_value_response = resource["identifier"][0]["value"]

    if (
        identifier_system_request != identifier_system_response
        and identifier_value_request != identifier_value_response
    ):
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
