from typing import TypedDict

"""Constants used by API clients"""

DEV_ENVIRONMENT = "dev"


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


GRANT_TYPE_CLIENT_CREDENTIALS = "client_credentials"
CLIENT_ASSERTION_TYPE_JWT_BEARER = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
CONTENT_TYPE_X_WWW_FORM_URLENCODED = "application/x-www-form-urlencoded"

JWT_EXPIRY_SECONDS = 5 * 60
ACCESS_TOKEN_EXPIRY_SECONDS = 10 * 60
# Throw away the cached token earlier than the exact expiry time so we have enough
# time left to use it (and to account for network latency, clock skew etc.)
ACCESS_TOKEN_MIN_ACCEPTABLE_LIFETIME_SECONDS = 30
