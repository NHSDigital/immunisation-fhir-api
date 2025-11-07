import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from common.models.errors import ApiValidationError, Severity, create_operation_outcome


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
class UnhandledResponseError(RuntimeError):
    """Use this error when the response from an external service (ex: dynamodb) can't be handled"""

    # Differs from errors.py in that code is Code.server.error rather than Code.exception
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
class UnauthorizedError(RuntimeError):
    # The Unauthorized*Error classes differ from errors.py in that they carry no arguments
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


class MandatoryError(Exception):
    def __init__(self, message=None):
        self.message = message


@dataclass
class InvalidImmunizationId(ApiValidationError):
    """Use this when the unique Immunization ID is invalid"""

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics="Validation errors: the provided event ID is either missing or not in the expected format.",
        )


@dataclass
class InvalidPatientId(ApiValidationError):
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
class InvalidResourceVersion(ApiValidationError):
    """Use this when the resource version is invalid"""

    resource_version: Any

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invariant,
            diagnostics=f"Validation errors: Immunization resource version:{self.resource_version} in the request "
            f"headers is invalid.",
        )


@dataclass
class InconsistentIdentifierError(ApiValidationError):
    """Use this when the local identifier in the payload does not match the existing identifier for the update."""

    msg: str

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.invariant, diagnostics=self.msg
        )


@dataclass
class InconsistentIdError(ApiValidationError):
    """Use this when the specified id in the message is inconsistent with the path
    see: http://hl7.org/fhir/R4/http.html#update"""

    imms_id: str

    def __str__(self):
        return (
            f"Validation errors: The provided immunization id:{self.imms_id} doesn't match with the content of the "
            f"request body"
        )

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invariant,
            diagnostics=self.__str__(),
        )


@dataclass
class InconsistentResourceVersion(ApiValidationError):
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
class InvalidJsonError(RuntimeError):
    """Raised when client provides an invalid JSON payload"""

    message: str

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics=self.message,
        )
