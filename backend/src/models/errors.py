import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Union


class Severity(str, Enum):
    error = "error"
    warning = "warning"


class Code(str, Enum):
    forbidden = "forbidden"
    not_found = "not-found"
    invalid = "invalid"
    server_error = "exception"
    invariant = "invariant"
    not_supported = "not-supported"
    duplicate = "duplicate"
    # Added an unauthorized code its used when returning a response for an unauthorized vaccine type search.
    unauthorized = "unauthorized"


@dataclass
class UnauthorizedError(RuntimeError):
    @staticmethod
    def to_operation_outcome() -> dict:
        msg = f"Unauthorized request"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=msg,
        )


@dataclass
class UnauthorizedVaxError(RuntimeError):
    @staticmethod
    def to_operation_outcome() -> dict:
        msg = "Unauthorized request for vaccine type"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=msg,
        )


@dataclass
class UnauthorizedVaxOnRecordError(RuntimeError):
    @staticmethod
    def to_operation_outcome() -> dict:
        msg = "Unauthorized request for vaccine type present in the stored immunization resource"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=msg,
        )


@dataclass
class ResourceNotFoundError(RuntimeError):
    """Return this error when the requested FHIR resource does not exist"""

    resource_type: str
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
class UnhandledResponseError(RuntimeError):
    """Use this error when the response from an external service (ex: dynamodb) can't be handled"""

    response: Union[dict, str]
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


class MandatoryError(Exception):
    def __init__(self, message=None):
        self.message = message


class ValidationError(RuntimeError):
    def to_operation_outcome(self) -> dict:
        pass


@dataclass
class InvalidPatientId(ValidationError):
    """Use this when NHS Number is invalid or doesn't exist"""

    patient_identifier: str

    def __str__(self):
        return f"NHS Number: {self.patient_identifier} is invalid or it doesn't exist."

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=self.__str__(),
        )


@dataclass
class InconsistentIdError(ValidationError):
    """Use this when the specified id in the message is inconsistent with the path
    see: http://hl7.org/fhir/R4/http.html#update"""

    imms_id: str

    def __str__(self):
        return f"The provided id:{self.imms_id} doesn't match with the content of the message"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=self.__str__(),
        )


@dataclass
class CustomValidationError(ValidationError):
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


@dataclass
class ParameterException(RuntimeError):
    message: str

    def __str__(self):
        return self.message


@dataclass
class UnauthorizedSystemError(RuntimeError):
    @staticmethod
    def to_operation_outcome() -> dict:
        msg = f"Unauthorized system"
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=msg,
        )