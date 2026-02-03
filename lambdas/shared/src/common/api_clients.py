import time

import requests

from common.clients import logger
from common.models.constants import Constants
from common.models.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    ResourceNotFoundError,
    ServerError,
    TokenValidationError,
    UnhandledResponseError,
)


def raise_error_response(response):
    error_mapping = {
        401: (TokenValidationError, "Token validation failed for the request"),
        400: (BadRequestError, "Bad request"),
        403: (ForbiddenError, "Forbidden: You do not have permission to access this resource"),
        404: (ResourceNotFoundError, "Resource not found"),
        408: (ServerError, "Request Timeout"),
        409: (ConflictError, "Conflict: Resource already exists"),
        429: (ServerError, "Too Many Requests"),
        500: (ServerError, "Internal Server Error"),
        502: (ServerError, "Bad Gateway"),
        503: (ServerError, "Service Unavailable"),
        504: (ServerError, "Gateway Timeout"),
    }

    exception_class, error_message = error_mapping.get(
        response.status_code,
        (UnhandledResponseError, f"Unhandled error: {response.status_code}"),
    )

    logger.info(f"{error_message}. Status={response.status_code}. Body={response.text}")

    if response.status_code == 404:
        raise exception_class(resource_type=response.json(), resource_id=error_message)
    raise exception_class(response=response.json(), message=error_message)


def request_with_retry_backoff(
    method: str, url: str, headers: dict, timeout: int = Constants.DEFAULT_API_CLIENTS_TIMEOUT, data: dict | None = None
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
        data (dict | None): Optional data to include in the request body.
    """
    response = None

    api_request_kwargs = {
        "method": method,
        "url": url,
        "headers": headers,
        "timeout": timeout,
    }

    for request_attempt in range(Constants.API_CLIENTS_MAX_RETRIES + 1):
        if data is not None:
            api_request_kwargs["data"] = data

        response = requests.request(**api_request_kwargs)
        if response.status_code not in Constants.RETRYABLE_STATUS_CODES:
            break

        if request_attempt < Constants.API_CLIENTS_MAX_RETRIES:
            logger.info(
                f"Retryable response. Status={response.status_code}. "
                f"Attempt={request_attempt + 1}/{Constants.API_CLIENTS_MAX_RETRIES + 1}. Retrying..."
            )

            time.sleep(Constants.API_CLIENTS_BACKOFF_SECONDS * (2**request_attempt))

    return response
