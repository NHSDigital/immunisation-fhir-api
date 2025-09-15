"""Module for the batch processor filter Lambda exception wrapper"""
from functools import wraps
from typing import Callable

from exceptions import EventAlreadyProcessingForSupplierAndVaccTypeError
from logger import logger


def exception_decorator(func: Callable):
    """Wrapper for the Lambda Handler. It ensures that any unhandled exceptions are logged for monitoring and alerting
    purposes."""

    @wraps(func)
    def exception_wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except EventAlreadyProcessingForSupplierAndVaccTypeError as exc:
            # Re-raise so event will be returned to SQS and retried for this expected error
            raise exc
        except Exception as exc:  # pylint:disable = broad-exception-caught
            logger.error("An unhandled exception occurred in the batch processor filter Lambda", exc_info=exc)
            raise exc

    return exception_wrapper
