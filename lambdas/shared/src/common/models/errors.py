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
    exception = "exception"
    server_error = "internal server error"
    invariant = "invariant"
    incomplete = "parameter-incomplete"
    not_supported = "not-supported"
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
class UnauthorizedVaxError(RuntimeError):
    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

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
    response: dict | str
    message: str

    def __str__(self):
        return f"{self.message}\n{self.response}"

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


@dataclass
class ResourceVersionNotProvided(RuntimeError):
    """Return this error when client has failed to provide the FHIR resource version where required"""

    resource_type: str

    def __str__(self):
        return f"Validation errors: {self.resource_type} resource version not specified in the request headers"

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invariant,
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


class ApiValidationError(RuntimeError):
    def to_operation_outcome(self) -> dict:
        pass


class UnhandledAuditTableError(Exception):
    """A custom exception for when an unexpected error occurs whilst adding the file to the audit table."""


class VaccineTypePermissionsError(Exception):
    """A custom exception for when the supplier does not have the necessary vaccine type permissions."""


class InvalidFileKeyError(Exception):
    """A custom exception for when the file key is invalid."""


class UnhandledSqsError(Exception):
    """A custom exception for when an unexpected error occurs whilst sending a message to SQS."""


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
class ParameterException(RuntimeError):
    message: str

    def __str__(self):
        return self.message


class UnauthorizedSystemError(RuntimeError):
    def __init__(self, message="Unauthorized system"):
        super().__init__(message)
        self.message = message

    def to_operation_outcome(self) -> dict:
        return create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.forbidden,
            diagnostics=self.message,
        )


class MessageNotSuccessfulError(Exception):
    """
    Generic error message for any scenario which either prevents sending to the Imms API, or which results in a
    non-successful response from the Imms API
    """

    def __init__(self, message=None):
        self.message = message


class RecordProcessorError(Exception):
    """
    Exception for re-raising exceptions which have already occurred in the Record Processor.
    The diagnostics dictionary received from the Record Processor is passed to the exception as an argument
    and is stored as an attribute.
    """

    def __init__(self, diagnostics_dictionary: dict):
        self.diagnostics_dictionary = diagnostics_dictionary


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
