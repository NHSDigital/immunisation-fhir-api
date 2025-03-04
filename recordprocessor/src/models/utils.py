import uuid
from dataclasses import dataclass
from typing import Union
from enum import Enum


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


@dataclass
class ImmunizationApiUnhandledError(RuntimeError):
    """An error that occurs when the ImmunizationApi throws an unhandled error."""

    request: dict


@dataclass
class ImmunizationApiError(RuntimeError):
    """An error that occurs when the ImmunizationApi returns a non-200 status code."""

    status_code: int
    request: dict
    response: Union[dict, str]


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
