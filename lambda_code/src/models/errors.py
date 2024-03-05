import uuid
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    error = "error"


class Code(str, Enum):
    not_found = "not-found"
    invalid = "invalid"
    server_error = "internal-server-error"
    invariant = "invariant"
    unprocessable_entity = "unprocessable_entity"


@dataclass
class ResourceNotFoundError(RuntimeError):
    """Return this error when the requested FHIR resource does not exist"""

    resource_type: str
    resource_id: str

    def __str__(self):
        return f"{self.resource_type} resource does not exist. ID: {self.resource_id}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.not_found, diagnostics=self.__str__()
        )


@dataclass
class UnhandledResponseError(RuntimeError):
    """Use this error when the response from an external service (ex: dynamodb) can't be handled"""

    response: dict
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.server_error, diagnostics=self.__str__()
        )


class ValidationError(RuntimeError):
    def to_operation_outcome(self) -> dict:
        pass


@dataclass
class InvalidPatientId(ValidationError):
    """Use this when NHS Number is invalid or doesn't exist"""

    nhs_number: str

    def __str__(self):
        return f"NHS Number: {self.nhs_number} is invalid or it doesn't exist."

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.server_error, diagnostics=self.__str__()
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
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.server_error, diagnostics=self.__str__()
        )


@dataclass
class CustomValidationError(ValidationError):
    """Custom validation error"""

    message: str

    def __str__(self):
        return self.message

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.invariant, diagnostics=self.__str__()
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
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.unprocessable_entity, diagnostics=msg
        )


def create_operation_outcome(resource_id: str, severity: Severity, code: Code, diagnostics: str) -> dict:
    """Create an OperationOutcome object. Do not use `fhir.resource` library since it adds unnecessary validations"""
    return {
        "resourceType": "OperationOutcome",
        "id": resource_id,
        "issue": [{"severity": severity, "code": code, "diagnostics": diagnostics}],
    }
