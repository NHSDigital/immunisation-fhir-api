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
        500: (ServerError, "Internal Server Error"),
        404: (ResourceNotFoundError, "Resource not found"),
        409: (ConflictError, "Conflict: Resource already exists"),
        408: (ServerError, "Request Timeout"),
        429: (ServerError, "Too Many Requests"),
        503: (ServerError, "Service Unavailable"),
        502: (ServerError, "Bad Gateway"),
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


def request_with_retry_backoff(method: str, url: str, headers: dict):
    """Makes an external request with retry and exponential backoff for retryable status codes."""
    response = None

    for request_attempt in range(Constants.API_CLIENTS_MAX_RETRIES + 1):
        response = requests.request(method, url, headers=headers, timeout=Constants.API_CLIENTS_TIMEOUT_SECONDS)
        if response.status_code not in Constants.RETRYABLE_STATUS_CODES:
            break

        if request_attempt < Constants.API_CLIENTS_MAX_RETRIES:
            logger.info(
                f"Retryable response. Status={response.status_code}. "
                f"Attempt={request_attempt + 1}/{Constants.API_CLIENTS_MAX_RETRIES + 1}. Retrying..."
            )

            time.sleep(Constants.API_CLIENTS_BACKOFF_SECONDS * (2**request_attempt))

    return response
