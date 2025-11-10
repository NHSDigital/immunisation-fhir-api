"""Module for the global FHIR API exception handler"""

import functools
import uuid
from typing import Callable, Type

from common.clients import logger
from common.models.constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE
from common.models.api_errors import (
    Code,
    InconsistentIdentifierError,
    InconsistentIdError,
    InconsistentResourceVersion,
    InvalidImmunizationId,
    InvalidJsonError,
    InvalidResourceVersion,
    Severity,
    UnauthorizedError,
    UnauthorizedVaxError,
    UnhandledResponseError,
    create_operation_outcome,
)
from common.models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    ResourceNotFoundError,
    ResourceVersionNotProvided,
)
from controller.aws_apig_response_utils import create_response

_CUSTOM_EXCEPTION_TO_STATUS_MAP: dict[Type[Exception], int] = {
    InconsistentResourceVersion: 400,
    InconsistentIdentifierError: 400,  # Identifier refers to the local FHIR identifier composed of system and value.
    InconsistentIdError: 400,  # ID refers to the top-level ID of the FHIR resource.
    InvalidImmunizationId: 400,
    InvalidJsonError: 400,
    InvalidResourceVersion: 400,
    CustomValidationError: 400,
    ResourceVersionNotProvided: 400,
    UnauthorizedError: 403,
    UnauthorizedVaxError: 403,
    ResourceNotFoundError: 404,
    IdentifierDuplicationError: 422,
    UnhandledResponseError: 500,
}


def fhir_api_exception_handler(function: Callable) -> Callable:
    """Decorator to handle any expected FHIR API exceptions or unexpected exception and provide a valid response to
    the client"""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except tuple(_CUSTOM_EXCEPTION_TO_STATUS_MAP) as exc:
            status_code = _CUSTOM_EXCEPTION_TO_STATUS_MAP[type(exc)]
            return create_response(status_code=status_code, body=exc.to_operation_outcome())
        except Exception:  # pylint: disable = broad-exception-caught
            logger.exception("Unhandled exception")
            server_error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.server_error,
                diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
            )
            return create_response(500, server_error)

    return wrapper
