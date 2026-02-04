"""Constants used by API clients"""


class Constants:
    """Constants used for the API clients"""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    DEFAULT_API_CLIENTS_TIMEOUT = 5
    API_CLIENTS_MAX_RETRIES = 2
    API_CLIENTS_BACKOFF_SECONDS = 0.5
