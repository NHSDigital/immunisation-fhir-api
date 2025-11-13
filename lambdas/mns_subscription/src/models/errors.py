import uuid
from dataclasses import dataclass

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
