import json
import os
import uuid

from common.get_service_url import get_service_url
from constants import IMMUNISATION_TYPE, SPEC_VERSION, SQSEventFields
from helper import find_imms_value_in_stream

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")

IMMUNIZATION_URL = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)


def create_mns_notification(sqs_event: dict) -> dict:
    """Create a notification payload for MNS."""

    immunisation_url = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)
    incoming_sqs_message = json.loads(sqs_event["body"])

    imms_data = {field: find_imms_value_in_stream(incoming_sqs_message, field.value) for field in SQSEventFields}

    return {
        "specversion": SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "source": IMMUNIZATION_URL,
        "type": IMMUNISATION_TYPE,
        "time": imms_data[SQSEventFields.DATE_AND_TIME_KEY],
        "subject": imms_data[SQSEventFields.NHS_NUMBER_KEY],
        "dataref": f"{immunisation_url}/Immunization/{imms_data[SQSEventFields.IMMUNISATION_ID_KEY]}",
        "filtering": {
            "generalpractitioner": "fy4563",
            "sourceorganisation": imms_data[SQSEventFields.SOURCE_ORGANISATION_KEY],
            "sourceapplication": imms_data[SQSEventFields.SOURCE_APPLICATION_KEY],
            "subjectage": "17",
            "immunisationtype": imms_data[SQSEventFields.VACCINE_TYPE],
            "action": imms_data[SQSEventFields.ACTION],
        },
    }


def fetch_details_from_pds(nhs_number: str) -> dict:
    """Fetch patient details from PDS using the NHS number."""
    # Placeholder for PDS integration logic
    # This function would typically make an API call to PDS to retrieve patient details
    return None
