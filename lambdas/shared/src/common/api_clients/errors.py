import uuid
from dataclasses import dataclass

from common.clients import logger
from common.models.errors import Code, Severity, create_operation_outcome


@dataclass
class UnauthorizedError(RuntimeError):
    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    @staticmethod
    def to_operation_outcome() -> dict:
        msg = "Unauthorized request"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=msg,
        )


@dataclass
class TokenValidationError(RuntimeError):
    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    @staticmethod
    def to_operation_outcome() -> dict:
        msg = "Missing/Invalid Token"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics=msg,
        )


@dataclass
class ForbiddenError(Exception):
    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    @staticmethod
    def to_operation_outcome() -> dict:
        msg = "Forbidden"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=msg,
        )


@dataclass
class ConflictError(RuntimeError):
    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    @staticmethod
    def to_operation_outcome() -> dict:
        msg = "Conflict"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.duplicate,
            diagnostics=msg,
        )


@dataclass
class BadRequestError(RuntimeError):
    """Use when payload is missing required parameters"""

    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.incomplete,
            diagnostics=self.__str__(),
        )


@dataclass
class ServerError(RuntimeError):
    """Use when there is a server error"""

    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=self.__str__(),
        )


@dataclass
class ResourceNotFoundError(RuntimeError):
    """Return this error when the requested FHIR resource does not exist"""

    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.not_found,
            diagnostics=self.__str__(),
        )


@dataclass
class UnhandledResponseError(RuntimeError):
    """Use this error when the response from an external service (ex: dynamodb) can't be handled"""

    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.exception,
            diagnostics=self.__str__(),
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

    raise exception_class(response=response.json(), message=error_message)
