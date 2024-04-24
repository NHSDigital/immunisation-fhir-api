from dataclasses import dataclass
from typing import List, Union


class NoneThrowingError:
    """A base class to mark errors that should not be thrown."""


@dataclass
class TransformerFieldError(NoneThrowingError):
    """An error that occurs during transformation of a field or a collection of fields like patient"""
    message: str
    field: str

    def __str__(self):
        return self.message


@dataclass
class DecoratorError(NoneThrowingError):
    """An error that accumulates all the errors that occur during decoration.
    It contains a collection of all field errors in the row."""
    errors: List[TransformerFieldError]
    decorator_name: str

    def __str__(self):
        errors = "\n".join([f"    {str(e)}" for e in self.errors])
        return f"  Decorator {self.decorator_name} failed due to:\n{errors}"


@dataclass
class TransformerRowError(RuntimeError):
    """An error that occurs during transformation of a row. It contains a collection of all decorators."""
    errors: List[DecoratorError]

    def __str__(self):
        errors = "\n".join([str(e) for e in self.errors])
        return f"Row transformation failed due to:\n{errors}"


@dataclass
class TransformerUnhandledError(RuntimeError):
    """An error that occurs when a decorator throws an error.
    A decorator should not throw an error. So any Exception is considered an unhandled error.
    NOTE: This differentiation is so we can identify bugs in handling CSV data or when we are dealing with unknown CSV.
    """
    decorator_name: str


@dataclass
class ImmunizationApiError(RuntimeError):
    """An error that occurs when the ImmunizationApi returns a non-200 status code."""
    status_code: int
    request: dict
    response: Union[dict, str]


@dataclass
class ImmunizationApiUnhandledError(RuntimeError):
    """An error that occurs when the ImmunizationApi throws an unhandled error."""
    request: dict
