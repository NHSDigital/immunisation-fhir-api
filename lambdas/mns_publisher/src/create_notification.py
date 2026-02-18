import json
import os
import uuid
from datetime import datetime

from common.api_clients.get_pds_details import pds_get_patient_details
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
    gp_ods_code = pds_get_patient_details(imms_data[SQSEventFields.NHS_NUMBER_KEY])

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
    birth_str = birth_date[:8] if len(birth_date) >= 8 else birth_date
    vacc_str = vaccination_date[:8] if len(vaccination_date) >= 8 else vaccination_date

    birth = datetime.strptime(birth_str, "%Y%m%d")
    vacc = datetime.strptime(vacc_str, "%Y%m%d")

    age = vacc.year - birth.year
    if (vacc.month, vacc.day) < (birth.month, birth.day):
        age -= 1

    return age
