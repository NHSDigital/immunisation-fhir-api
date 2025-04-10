import json
import os
import uuid
import boto3
from copy import deepcopy
from decimal import Decimal
from typing import Union, Literal
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from botocore.config import Config
from .mappings import vaccine_type_mappings, VaccineTypes
from .constants import valid_nhs_number1

current_directory = os.path.dirname(os.path.realpath(__file__))


def load_example(path: str) -> dict:
    with open(f"{current_directory}/../../specification/components/examples/{path}") as f:
        return json.load(f, parse_float=Decimal)


def generate_imms_resource(
    nhs_number=valid_nhs_number1,
    vaccine_type=VaccineTypes.covid_19,
    imms_identifier_value: str = None,
    occurrence_date_time: str = None,
    sample_data_file_name: str = "completed_[vaccine_type]_immunization_event",
) -> dict:
    """
    Creates a FHIR Immunization Resource dictionary, which includes an id, using the sample data for the given
    vaccine type as a base, and updates the id, nhs_number and occurrence_date_time as required.
    The unique_identifier is also updated to ensure uniqueness...
    """
    # Load the data
    sample_data_file_name = sample_data_file_name.replace("[vaccine_type]", vaccine_type.lower())
    imms = deepcopy(load_example(f"Immunization/{sample_data_file_name}.json"))

    # Apply identifier directly
    imms["identifier"][0]["value"] = imms_identifier_value or str(uuid.uuid4())

    if nhs_number is not None:
        imms["contained"][1]["identifier"][0]["value"] = nhs_number

    if occurrence_date_time is not None:
        imms["occurrenceDateTime"] = occurrence_date_time

    return imms


def generate_filtered_imms_resource(
    crud_operation_to_filter_for: Literal["READ", "SEARCH", ""] = "",
    nhs_number=valid_nhs_number1,
    imms_identifier_value: str = None,
    vaccine_type=VaccineTypes.covid_19,
    occurrence_date_time: str = None,
) -> dict:
    """
    Creates a filtered FHIR Immunization Resource dictionary, which includes an id, using the sample filtered data for
    the given vaccine type, crud operation (if specified) as a base, and updates the id,
    nhs_number and occurrence_date_time as required.

    NOTE: The filtered sample data files use the corresponding unfiltered sample data files as a base, and this
    function can therefore be used in combination with the create_an_imms_obj function for testing filtering.
    NOTE: New sample data files can be added by copying the sample data file for the releavant vaccine type and
    removing, obfuscating or amending the relevant fields as required.
    The new file name must be consistent with the existing sample data file names.
    """
    # Load the data
    file_name = (
        f"Immunization/completed_{vaccine_type.lower()}_immunization_event"
        + f"_filtered_for_{crud_operation_to_filter_for.lower()}"
    )
    imms = deepcopy(load_example(f"{file_name}.json"))
    # Apply identifier directly
    imms["identifier"][0]["value"] = imms_identifier_value or str(uuid.uuid4())

    # Note that NHS number is found in a different place on a search return
    if crud_operation_to_filter_for == "SEARCH":
        imms["patient"]["identifier"]["value"] = nhs_number
    else:
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
        raise ValueError(
            f"protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - "
            f"{disease_codes_input} is not a valid combination of disease codes for this service"
        ) from e


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


def get_patient_postal_code(imms: dict):
    patients = [record for record in imms.get("contained", []) if record.get("resourceType") == "Patient"]
    if patients:
        return patients[0]["address"][0]["postalCode"]
    return ""


def get_full_row_from_identifier(identifier: str) -> dict:
    table = get_dynamodb_table()

    return table.get_item(Key={"PK": f"Immunization#{identifier}"}).get("Item")


def get_dynamodb_table() -> Table:
    config = Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 1})
    db: DynamoDBServiceResource = boto3.resource("dynamodb", region_name="eu-west-2", config=config)
    return db.Table(os.getenv("DYNAMODB_TABLE_NAME"))


def delete_imms_records(identifiers: list[str]) -> dict:
    """Batch delete immunization records from the DynamoDB table.
    Returns counts of successful and failed deletions.
    """
    table = get_dynamodb_table()
    success_count = 0
    failure_count = 0

    try:
        with table.batch_writer(overwrite_by_pkeys=["PK"]) as batch:
            for identifier in identifiers:
                key = {"PK": f"Immunization#{identifier}"}
                try:
                    batch.delete_item(Key=key)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to delete record with key {key}: {e}")
                    failure_count += 1
    except Exception as e:
        print(f"Batch writer failed: {e}")
        return {"success_count": success_count, "failure_count": len(identifiers)}

    return {"success_count": success_count, "failure_count": failure_count}
