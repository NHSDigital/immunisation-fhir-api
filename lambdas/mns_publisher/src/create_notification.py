import json
import os
import uuid
from datetime import datetime

from common.api_clients.get_pds_details import pds_get_patient_details
from common.clients import logger
from common.get_service_url import get_service_url
from constants import IMMUNISATION_TYPE, SPEC_VERSION, SQSEventFields
from sqs_dynamo_utils import find_imms_value_in_stream

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")
PDS_BASE_URL = os.getenv("PDS_BASE_URL")


def create_mns_notification(sqs_event: dict) -> dict:
    """Create a notification payload for MNS."""

    immunisation_url = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)
    incoming_sqs_message = json.loads(sqs_event["body"])

    imms_data = {field: find_imms_value_in_stream(incoming_sqs_message, field.value) for field in SQSEventFields}

    patient_age = calculate_age_at_vaccination(
        imms_data[SQSEventFields.BIRTH_DATE_KEY], imms_data[SQSEventFields.DATE_AND_TIME_KEY]
    )

    gp_ods_code = get_practitioner_details_from_pds(imms_data[SQSEventFields.NHS_NUMBER_KEY])

    return {
        "specversion": SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "source": immunisation_url,
        "type": IMMUNISATION_TYPE,
        "time": imms_data[SQSEventFields.DATE_AND_TIME_KEY],
        "subject": imms_data[SQSEventFields.NHS_NUMBER_KEY],
        "dataref": f"{immunisation_url}/Immunization/{imms_data[SQSEventFields.IMMUNISATION_ID_KEY]}",
        "filtering": {
            "generalpractitioner": gp_ods_code,
            "sourceorganisation": imms_data[SQSEventFields.SOURCE_ORGANISATION_KEY],
            "sourceapplication": imms_data[SQSEventFields.SOURCE_APPLICATION_KEY],
            "subjectage": str(patient_age),
            "immunisationtype": imms_data[SQSEventFields.VACCINE_TYPE],
            "action": imms_data[SQSEventFields.ACTION],
        },
    }


def calculate_age_at_vaccination(birth_date: str, vaccination_date: str) -> int:
    """
    Calculate patient age in years at time of vaccination.
    Expects dates in format: YYYYMMDD or YYYYMMDDTHHmmss
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
    try:
        patient_details = pds_get_patient_details(nhs_number)
        patient_gp = patient_details.get("generalPractitioner")
        if not patient_gp:
            logger.warning("No patient details found for NHS number")
            return None

        gp_ods_code = patient_gp.get("value")
        if not gp_ods_code:
            logger.warning("GP ODS code not found in practitioner details")
            return None

        return gp_ods_code
    except Exception as error:
        logger.exception("Failed to get practitioner details from pds", error)
        raise
