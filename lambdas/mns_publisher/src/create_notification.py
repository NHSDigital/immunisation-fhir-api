import datetime
import json
import os
import uuid

from common.api_clients import get_patient_details_from_pds
from common.get_service_url import get_service_url
from constants import IMMUNISATION_TYPE, SPEC_VERSION, SQSEventFields
from helper import find_imms_value_in_stream

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
    gp_ods_code = (
        get_patient_details_from_pds(imms_data[SQSEventFields.NHS_NUMBER_KEY], PDS_BASE_URL)
        .get("generalPractitioner", [{}])[0]
        .get("identifier", {})
        .get("value", "unknown")
    )

    return {
        "specversion": SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "source": immunisation_url,
        "type": IMMUNISATION_TYPE,
        "time": imms_data[SQSEventFields.DATE_AND_TIME_KEY],
        "subject": imms_data[SQSEventFields.NHS_NUMBER_KEY],
        "dataref": f"{immunisation_url}/Immunization/{imms_data[SQSEventFields.IMMUNISATION_ID_KEY]}",
        "filtering": {
            "generalpractitioner": {gp_ods_code},
            "sourceorganisation": imms_data[SQSEventFields.SOURCE_ORGANISATION_KEY],
            "sourceapplication": imms_data[SQSEventFields.SOURCE_APPLICATION_KEY],
            "subjectage": str(patient_age),
            "immunisationtype": imms_data[SQSEventFields.VACCINE_TYPE],
            "action": imms_data[SQSEventFields.ACTION],
        },
    }


def calculate_age_at_vaccination(birth_date: str, vaccination_date: str) -> int:
    """Calculate patient age in years at time of vaccination."""
    birth = datetime.fromisoformat(birth_date.replace("Z", "+00:00"))
    vacc = datetime.fromisoformat(vaccination_date.replace("Z", "+00:00"))

    age = vacc.year - birth.year
    if (vacc.month, vacc.day) < (birth.month, birth.day):
        age -= 1

    return age
