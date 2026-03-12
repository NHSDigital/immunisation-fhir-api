from typing import TypedDict

"""Constants used by API clients"""

DEV_ENVIRONMENT = "dev"
API_CACHE_KEY = "api_client_access_token"


class Constants:
    """Constants used for the API clients"""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    DEFAULT_API_CLIENTS_TIMEOUT = 5
    API_CLIENTS_MAX_RETRIES = 2
    API_CLIENTS_BACKOFF_SECONDS = 0.5


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
