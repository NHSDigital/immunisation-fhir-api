import json
import os
import uuid
from datetime import datetime
from typing import Any

from aws_lambda_typing.events.sqs import SQSMessage

from common.api_clients.get_pds_details import pds_get_patient_details
from common.clients import logger
from common.get_service_url import get_service_url
from constants import DYNAMO_DB_TYPE_DESCRIPTORS, IMMUNISATION_TYPE, SPEC_VERSION, MnsNotificationPayload

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")


def create_mns_notification(sqs_event: SQSMessage) -> MnsNotificationPayload:
    """Create a notification payload for MNS."""
    immunisation_url = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)

    body = json.loads(sqs_event.get("body", "{}"))
    new_image = body.get("dynamodb", {}).get("NewImage", {})
    imms_id = _unwrap_dynamodb_value(new_image.get("ImmsID", {}))
    supplier_system = _unwrap_dynamodb_value(new_image.get("SupplierSystem", {}))
    vaccine_type = _unwrap_dynamodb_value(new_image.get("VaccineType", {}))
    operation = _unwrap_dynamodb_value(new_image.get("Operation", {}))

    imms_map = new_image.get("Imms", {}).get("M", {})
    nhs_number = _unwrap_dynamodb_value(imms_map.get("NHS_NUMBER", {}))
    if not nhs_number:
        logger.error("Missing required field: Nhs Number")
        raise ValueError("NHS number is required to create MNS notification")

    person_dob = _unwrap_dynamodb_value(imms_map.get("PERSON_DOB", {}))
    date_and_time = _unwrap_dynamodb_value(imms_map.get("DATE_AND_TIME", {}))
    site_code = _unwrap_dynamodb_value(imms_map.get("SITE_CODE", {}))

    patient_age = calculate_age_at_vaccination(person_dob, date_and_time)
    gp_ods_code = get_practitioner_details_from_pds(nhs_number)

    return {
        "specversion": SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "source": immunisation_url,
        "type": IMMUNISATION_TYPE,
        "time": date_and_time,
        "subject": nhs_number,
        "dataref": f"{immunisation_url}/Immunization/{imms_id}",
        "filtering": {
            "generalpractitioner": gp_ods_code,
            "sourceorganisation": site_code,
            "sourceapplication": supplier_system,
            "subjectage": patient_age,
            "immunisationtype": vaccine_type.upper(),
            "action": operation,
        },
    }


def calculate_age_at_vaccination(birth_date: str, vaccination_date: str) -> int:
    """
    Calculate patient age in years at time of vaccination.
    Expects dates in format: YYYYMMDD or YYYYMMDDThhmmsszz
    """
    birth_date_str = birth_date[:8] if len(birth_date) >= 8 else birth_date
    vacc_date_str = vaccination_date[:8] if len(vaccination_date) >= 8 else vaccination_date

    date_of_birth = datetime.strptime(birth_date_str, "%Y%m%d")
    date_of_vaccination = datetime.strptime(vacc_date_str, "%Y%m%d")

    age_in_year = date_of_vaccination.year - date_of_birth.year
    if (date_of_vaccination.month, date_of_vaccination.day) < (date_of_birth.month, date_of_birth.day):
        age_in_year -= 1

    return age_in_year


def get_practitioner_details_from_pds(nhs_number: str) -> str | None:
    patient_details = pds_get_patient_details(nhs_number)
    if not patient_details:
        logger.info("Unable to retrieve patient details")
        return None

    general_practitioners = patient_details.get("generalPractitioner", [])
    if not general_practitioners or len(general_practitioners) == 0:
        logger.warning("No GP details found for patient")
        return None

    patient_gp = general_practitioners[0]
    patient_gp_identifier = patient_gp.get("identifier", {})

    gp_ods_code = patient_gp_identifier.get("value")
    if not gp_ods_code:
        logger.warning("GP ODS code not found in practitioner details")
        return None

    # Check if registration is current
    period = patient_gp_identifier.get("period", {})
    gp_period_end_date = period.get("end", None)

    if gp_period_end_date:
        # Parse end date (format: YYYY-MM-DD)
        end_date = datetime.strptime(gp_period_end_date, "%Y-%m-%d").date()
        today = datetime.now().date()

        if end_date < today:
            logger.warning("No current GP registration found for patient")
            return None

    return gp_ods_code


def _unwrap_dynamodb_value(value: dict) -> Any:
    """
    Unwrap DynamoDB type descriptor to get the actual value.
    DynamoDB types: S (String), N (Number), BOOL, M (Map), L (List), NULL
    """
    if not isinstance(value, dict):
        return value

    if "NULL" in value:
        return None

    for key in DYNAMO_DB_TYPE_DESCRIPTORS:
        if key in value:
            return value[key]

    return value
