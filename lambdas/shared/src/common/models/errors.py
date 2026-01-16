import uuid
from dataclasses import dataclass
from enum import Enum


class Code(str, Enum):
    forbidden = "forbidden"
    not_found = "not-found"
    invalid = "invalid or missing access token"
    exception = "exception"
    server_error = "internal server error"
    invariant = "invariant"
    incomplete = "parameter-incomplete"
    not_supported = "not-supported"
    duplicate = "duplicate"
    # Added an unauthorized code its used when returning a response for an unauthorized vaccine type search.
    unauthorized = "unauthorized"


class Severity(str, Enum):
    error = "error"
    warning = "warning"


class MandatoryError(Exception):
    def __init__(self, message=None):
        self.message = message


@dataclass
class ResourceNotFoundError(RuntimeError):
    """Return this error when the requested FHIR resource does not exist"""

    resource_type: str | None
    resource_id: str

    def __str__(self):
        return f"{self.resource_type} resource does not exist. ID: {self.resource_id}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.not_found,
            diagnostics=self.__str__(),
        )


@dataclass
class ResourceFoundError(RuntimeError):
    """Return this error when the requested FHIR resource does exist"""

    resource_type: str
    resource_id: str

    def __str__(self):
        return f"{self.resource_type} resource does exist. ID: {self.resource_id}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.not_found,
            diagnostics=self.__str__(),
        )


class ApiValidationError(RuntimeError):
    def to_operation_outcome(self) -> dict:
        raise NotImplementedError("Improper usage: base class")


@dataclass
class InconsistentIdentifierError(ApiValidationError):
    """Use this when the local identifier in the payload does not match the existing identifier for the update."""

    msg: str

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.invariant, diagnostics=self.msg
        )


@dataclass
class InconsistentResourceVersionError(ApiValidationError):
    """Use this when the resource version in the request and actual resource version do not match"""

    message: str

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invariant,
            diagnostics=self.message,
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


@dataclass
class UnhandledAuditTableError(Exception):
    """A custom exception for when an unexpected error occurs whilst adding the file to the audit table."""

    message: str

    def __str__(self):
        return self.message


@dataclass
class CustomValidationError(ApiValidationError):
    """Custom validation error"""

    message: str

    def __str__(self):
        return self.message

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invariant,
            diagnostics=self.__str__(),
        )


@dataclass
class IdentifierDuplicationError(RuntimeError):
    """Fine grain validation"""

    identifier: str

    def __str__(self) -> str:
        return f"The provided identifier: {self.identifier} is duplicated"

    def to_operation_outcome(self) -> dict:
        msg = self.__str__()
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.duplicate,
            diagnostics=msg,
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
