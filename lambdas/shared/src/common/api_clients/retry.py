import time

import requests

from common.api_clients.constants import Constants
from common.clients import logger


def request_with_retry_backoff(
    method: str,
    url: str,
    headers: dict | None = None,
    timeout: int = Constants.DEFAULT_API_CLIENTS_TIMEOUT,
    max_retries: int = Constants.API_CLIENTS_MAX_RETRIES,
    data: dict | None = None,
) -> requests.Response:
    """
    Makes an external request with retry and exponential backoff for retryable status codes.
    Retries only for status codes in Constants.RETRYABLE_STATUS_CODES (e.g. 429/5xx),
    up to Constants.API_CLIENTS_MAX_RETRIES. Returns the final Response for the caller
    to handle (success or last failure after retries).
    Args:
        method (str): HTTP method (e.g. 'GET', 'POST', 'PUT', 'DELETE').
        url (str): The URL to send the request to.
        headers (dict): Headers to include in the request.
        timeout (int): Timeout for the request in seconds.
        max_retries (int): Maximum number of retries for retryable status codes.
        data (dict | None): Optional data to include in the request body.
    """
    response = None

    api_request_kwargs = {
        "method": method,
        "url": url,
        "headers": headers,
        "timeout": timeout,
    }

    for request_attempt in range(max_retries + 1):
        if data is not None:
            api_request_kwargs["data"] = data

        response = requests.request(**api_request_kwargs)
        if response.status_code not in Constants.RETRYABLE_STATUS_CODES:
            break

        if request_attempt < max_retries:
            logger.info(
                f"Retryable response. Status={response.status_code}. "
                f"Attempt={request_attempt + 1}/{max_retries + 1}. Retrying..."
            )

            time.sleep(Constants.API_CLIENTS_BACKOFF_SECONDS * (2**request_attempt))

    return response
