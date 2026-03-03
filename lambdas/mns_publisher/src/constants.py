from typing import TypedDict

# Static constants for the MNS notification creation process
SPEC_VERSION = "1.0"
IMMUNISATION_TYPE = "imms-vaccinations-1"


# Fields from the incoming SQS message that forms part of the base schema and filtering attributes for MNS notifications
class FilteringData(TypedDict):
    """MNS notification filtering attributes."""

    generalpractitioner: str | None
    sourceorganisation: str
    sourceapplication: str
    subjectage: int
    immunisationtype: str
    action: str


class MnsNotificationPayload(TypedDict):
    """CloudEvents-compliant MNS notification payload."""

    specversion: str
    id: str
    source: str
    type: str
    time: str
    subject: str
    dataref: str
    filtering: FilteringData


DYNAMO_DB_TYPE_DESCRIPTORS = ("S", "N", "BOOL", "M", "L")
