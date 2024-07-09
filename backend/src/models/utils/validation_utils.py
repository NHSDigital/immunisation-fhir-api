"""Utils for backend folder"""

import json


from typing import Union
from mappings import vaccine_type_mappings
from .generic_utils import create_diagnostics_error
from base_utils.base_utils import obtain_field_location
from models.obtain_field_value import ObtainFieldValue
from models.field_names import FieldNames
from models.errors import MandatoryError
from constants import Urls


def get_target_disease_codes(immunization: dict):
    """Takes a FHIR immunization resource and returns a list of target disease codes"""
    target_diseases = []
    try:
        target_disease_list = ObtainFieldValue.target_disease(immunization)
    except (KeyError, IndexError) as error:
        raise MandatoryError("No target disease codes found") from error

    for i, element in enumerate(target_disease_list):

        try:
            code = [x.get("code") for x in element["coding"] if x.get("system") == Urls.snomed][0]
        except (KeyError, IndexError) as error:
            raise MandatoryError(
                f"protocolApplied[0].targetDisease[{i}].coding[?(@.system=='http://snomed.info/sct')].code is a mandatory field"
            ) from error

        if code is None:
            raise ValueError(
                f"'None' is not a valid value for '{obtain_field_location(FieldNames.target_disease_codes)}'"
            )
        target_diseases.append(code)

    return target_diseases


def convert_disease_codes_to_vaccine_type(disease_codes_input: list) -> Union[str, None]:
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
        raise ValueError(
            f"protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - "
            f"{disease_codes_input} is not a valid combination of disease codes for this service"
        ) from e


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
    except AttributeError as error:
        raise ValueError("No target disease codes found") from error
    except MandatoryError as error:
        raise ValueError(str(error)) from error
    except ValueError as error:
        raise ValueError(f"{obtain_field_location(FieldNames.target_disease_codes)} is a mandatory field") from error

    # Convert list of target diseases to vaccine type
    return convert_disease_codes_to_vaccine_type(target_diseases)


def check_identifier_system_value(response, imms, app_id):
    """Returns diagnostics if identifier's system and value does not match with the stored content"""

    app_id_response = response["Item"].get("AppId", None)
    if app_id != app_id_response:
        value = "Unauthorized"
        diagnostics_error = create_diagnostics_error(value)
        return diagnostics_error

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
