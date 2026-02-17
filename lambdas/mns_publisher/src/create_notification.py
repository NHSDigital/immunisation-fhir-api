import json
import os

from common.get_service_url import get_service_url
from constants import IMMUNISATION_TYPE, SPEC_VERSION

IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")
IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")

IMMUNIZATION_URL = get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)


def create_mns_notification(event: dict) -> dict:
    """Create a notification payload for MNS."""

    incoming_sqs_message = json.loads(event["body"])

    return {
        "specversion": SPEC_VERSION,
        "id": incoming_sqs_message["eventID"],
        "source": IMMUNIZATION_URL,
        "type": IMMUNISATION_TYPE,
        "time": "2020-06-01T13:00:00Z",
        "subject": "",
        "dataref": "https://int.api.service.nhs.uk/immunisation-fhir-api/Immunization/29dc4e84-7e72-11ee-b962-0242ac120002",
    }
