import copy
import json
import os
import uuid
import boto3
from decimal import Decimal
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from botocore.config import Config
from .mappings import vaccine_type_mappings, VaccineTypes

from .constants import valid_nhs_number1

current_directory = os.path.dirname(os.path.realpath(__file__))


def load_example(path: str) -> dict:
    with open(f"{current_directory}/../../specification/components/examples/{path}") as f:
        return json.load(f, parse_float=Decimal)


def create_an_imms_obj(
    imms_id: str = str(uuid.uuid4()), nhs_number=valid_nhs_number1, vaccine_type=None, occurrence_date_time: str = None
) -> dict:
    imms = copy.deepcopy(load_example("Immunization/POST-COVID19-Immunization.json"))
    # TODO: VACCINE_TYPE remove unnecessary lines of code below
    if vaccine_type:
        target_diseases = []
        target_disease_list = imms["protocolApplied"][0]["targetDisease"]
        for element in target_disease_list:
            code = [x.get("code") for x in element["coding"] if x.get("system") == "http://snomed.info/sct"][0]
        target_diseases.append(code)
        [disease_type for codes, disease_type in vaccine_type_mappings if codes == target_diseases][0] = vaccine_type
        if vaccine_type == VaccineTypes.mmr:
            imms = copy.deepcopy(load_example("Immunization/POST-MMR-Immunization.json"))
        if vaccine_type == VaccineTypes.flu:
            imms = copy.deepcopy(load_example("Immunization/POST-822851000000102-FLU-Immunization.json"))
    imms["id"] = imms_id
    imms["identifier"][0]["value"] = str(uuid.uuid4())
    imms["contained"][1]["identifier"][0]["value"] = nhs_number
    if occurrence_date_time is not None:
        imms["occurrenceDateTime"] = occurrence_date_time

    return imms


def get_patient_id(imms: dict) -> str:
    patients = [resource for resource in imms["contained"] if resource["resourceType"] == "Patient"]
    return patients[0]["identifier"][0]["value"]


def get_vaccine_type(imms: dict) -> str:
    """find the vaccine code in the resource and map it to disease-type"""
    target_diseases = []
    target_disease_list = imms["protocolApplied"][0]["targetDisease"]
    for element in target_disease_list:
        code = [x.get("code") for x in element["coding"] if x.get("system") == "http://snomed.info/sct"][0]
    target_diseases.append(code)

    vaccine_type = [disease_type for codes, disease_type in vaccine_type_mappings if codes == target_diseases][0]
    return vaccine_type


def get_questionnaire_items(imms: dict):
    questionnaire = next(
        contained for contained in imms["contained"] if contained["resourceType"] == "QuestionnaireResponse"
    )
    return questionnaire["item"]


def get_full_row_from_identifier(identifier: str) -> dict:
    """
    Get the full record from the dynamodb table using the identifier
    """
    config = Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 1})
    db: DynamoDBServiceResource = boto3.resource("dynamodb", region_name="eu-west-2", config=config)
    table = db.Table(os.getenv("DYNAMODB_TABLE_NAME"))

    return table.get_item(Key={"PK": f"Immunization#{identifier}"}).get("Item")