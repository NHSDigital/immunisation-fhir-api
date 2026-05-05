import json
import os
import uuid
from datetime import date, datetime

from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import DynamoDBStreamEvent
from aws_lambda_typing.events.sqs import SQSMessage

from common.api_clients.constants import MnsNotificationPayload
from common.api_clients.get_pds_details import pds_get_patient_details
from common.clients import logger
from common.converter_utils import timestamp_to_rfc3339
from common.get_service_url import get_service_url
from constants import IMMUNISATION_EVENT_SOURCE, IMMUNISATION_EVENT_TYPE, SPEC_VERSION

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")


def create_mns_notification(sqs_event: SQSMessage) -> MnsNotificationPayload:
    """Create a notification payload for MNS."""
    immunisation_url = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)

    body = json.loads(sqs_event.get("body", "{}"))
    event = DynamoDBStreamEvent({"Records": [body]})
    record = next(event.records)
    new_image = record.dynamodb.new_image
    imms_id = new_image.get("ImmsID", {})
    supplier_system = new_image.get("SupplierSystem", "")
    vaccine_type = new_image.get("VaccineType", "")
    operation = new_image.get("Operation", "")

    imms_data = new_image.get("Imms", {})
    nhs_number = imms_data.get("NHS_NUMBER", "")
    if not nhs_number:
        logger.error("Missing required field: Nhs Number")
        raise ValueError("NHS number is required to create MNS notification")

    person_dob = imms_data.get("PERSON_DOB", "")
    date_and_time = imms_data.get("DATE_AND_TIME", "")
    site_code = imms_data.get("SITE_CODE", "")

    patient_age = calculate_age_at_vaccination(person_dob, date_and_time)
    gp_ods_code = get_practitioner_details_from_pds(nhs_number)
    mns_timestamp = timestamp_to_rfc3339(date_and_time)

    return {
        "specversion": SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "source": IMMUNISATION_EVENT_SOURCE,
        "type": IMMUNISATION_EVENT_TYPE,
        "time": mns_timestamp,
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


def _parse_compact_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")

    date_part = value[:8]
    if len(date_part) != 8 or not date_part.isdigit():
        raise ValueError(f"{field_name} must start with YYYYMMDD")

    try:
        return datetime.strptime(date_part, "%Y%m%d").date()
    except ValueError as e:
        raise ValueError(f"{field_name} must contain a valid date in YYYYMMDD format") from e


def calculate_age_at_vaccination(birth_date: str, vaccination_date: str) -> int:
    """
    Calculate patient age in years at time of vaccination.
    Expects dates in format: YYYYMMDD or YYYYMMDDThhmmsszz
    Note: This function performs a pure calculation and does not enforce domain validation.
    If the vaccination date precedes the birth date, a negative age may be returned.
    Validation of date correctness and logical consistency (e.g. vaccination after birth)
    is expected to be handled upstream in the data ingestion pipeline.
    """
    date_of_birth = _parse_compact_date(birth_date, "PERSON_DOB")
    date_of_vaccination = _parse_compact_date(vaccination_date, "DATE_AND_TIME")

    age = date_of_vaccination.year - date_of_birth.year
    if (date_of_vaccination.month, date_of_vaccination.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1

    return age


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
