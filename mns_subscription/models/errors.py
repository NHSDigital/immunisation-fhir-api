import uuid
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    error = "error"
    warning = "warning"


class Code(str, Enum):
    forbidden = "forbidden"
    not_found = "not-found"
    invalid = "invalid or missing access token"
    server_error = "internal server error"
    invariant = "invariant"
    incomplete = "parameter-incomplete"
    duplicate = "duplicate"
    # Added an unauthorized code its used when returning a response for an unauthorized vaccine type search.
    unauthorized = "unauthorized"


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
class ResourceNotFoundError(RuntimeError):
    """Return this error when the requested resource does not exist or not complete"""

    response: None
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
    """Use this unhandled errors"""

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


def create_operation_outcome(resource_id: str, severity: Severity, code: Code, diagnostics: str) -> dict:
    """Create an OperationOutcome object. Do not use `fhir.resource` library since it adds unnecessary validations"""
    return {
        "resourceType": "OperationOutcome",
        "id": resource_id,
        "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
        "issue": [
            {
                "severity": severity,
                "code": code,
                "details": {
                    "coding": [
                        {
                            "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                            "code": code.upper(),
                        }
                    ]
                },
                "diagnostics": diagnostics,
            }
        ],
    }
