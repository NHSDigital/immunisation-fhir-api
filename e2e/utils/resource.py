import json
import os
import uuid
import boto3
from copy import deepcopy
from decimal import Decimal
from typing import Union, Literal
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from botocore.config import Config
from .mappings import vaccine_type_mappings, VaccineTypes

from .constants import valid_nhs_number1

current_directory = os.path.dirname(os.path.realpath(__file__))


def load_example(path: str) -> dict:
    with open(f"{current_directory}/../../specification/components/examples/{path}") as f:
        return json.load(f, parse_float=Decimal)


def create_an_imms_obj(
    imms_id: str = str(uuid.uuid4()),
    nhs_number=valid_nhs_number1,
    vaccine_type=VaccineTypes.covid_19,
    occurrence_date_time: str = None,
) -> dict:
    """
    Creates a FHIR Immunization Resource dictionary, which includes an id, using the sample data for the given
    vaccine type as a base, and updates the id, nhs_number and occurrence_date_time as required.
    The unique_identifier is also updated to ensure uniqueness.
    """
    imms = deepcopy(load_example(f"Immunization/completed_{vaccine_type.lower()}_immunization_event_with_id.json"))
    imms["id"] = imms_id
    imms["identifier"][0]["value"] = str(uuid.uuid4())
    imms["contained"][1]["identifier"][0]["value"] = nhs_number
    if occurrence_date_time is not None:
        imms["occurrenceDateTime"] = occurrence_date_time

    return imms


def create_a_filtered_imms_obj(
    crud_operation_to_filter_for: Literal["READ", "SEARCH", ""] = "",
    filter_for_s_flag: bool = False,
    imms_id: str = str(uuid.uuid4()),
    nhs_number=valid_nhs_number1,
    vaccine_type=VaccineTypes.covid_19,
    occurrence_date_time: str = None,
) -> dict:
    """
    Creates a filtered FHIR Immunization Resource dictionary, which includes an id, using the sample filtered data for
    the given vaccine type, crud operation (if specified) and s_flag (if required) as a base, and updates the id,
    nhs_number and occurrence_date_time as required.

    NOTE: The filtered sample data files use the corresponding unfiltered sample data files as a base, and this
    function can therefore be used in combination with the create_an_imms_obj function for testing filtering.
    NOTE: New sample data files can be added by copying the sample data file for the releavant vaccine type and
    removing or obfuscating the relevant fields as required. The new file name must be consistent with the existing
    sample data file names.
    """
    # Load the data
    s_flag_string = "_and_s_flag" if filter_for_s_flag else ""
    file_name = (
        f"Immunization/completed_{vaccine_type.lower()}_immunization_event_with_id"
        + f"_filtered_for_{crud_operation_to_filter_for.lower()}{s_flag_string}"
    )
    imms = deepcopy(load_example(f"{file_name}.json"))

    # Amend values as required
    imms["id"] = imms_id
    imms["contained"][1]["identifier"][0]["value"] = nhs_number
    if occurrence_date_time is not None:
        imms["occurrenceDateTime"] = occurrence_date_time

    return imms


def get_patient_id(imms: dict) -> str:
    patients = [resource for resource in imms["contained"] if resource["resourceType"] == "Patient"]
    return patients[0]["identifier"][0]["value"]


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


def get_questionnaire_items(imms: dict):
    questionnaire = next(
        contained for contained in imms["contained"] if contained["resourceType"] == "QuestionnaireResponse"
    )
    return questionnaire["item"]


def get_patient_postal_code(self, imms: dict) -> str:
    patients = [record
            for record in imms.get("contained", [])
            if record.get("resourceType") == "Patient"]
    if patients:
        return patients[0]["address"][0]["postalCode"]
    return ""

def get_full_row_from_identifier(identifier: str) -> dict:
    """Get the full record from the dynamodb table using the identifier"""
    config = Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 1})
    db: DynamoDBServiceResource = boto3.resource("dynamodb", region_name="eu-west-2", config=config)
    table = db.Table(os.getenv("DYNAMODB_TABLE_NAME"))

    return table.get_item(Key={"PK": f"Immunization#{identifier}"}).get("Item")
