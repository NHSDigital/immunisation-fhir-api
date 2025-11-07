import json
import unittest
from unittest.mock import patch

from common.models.api_errors import (
    InconsistentIdentifierError,
    InconsistentIdError,
    InconsistentResourceVersion,
    InvalidJsonError,
    InvalidResourceVersion,
    UnauthorizedError,
    UnauthorizedVaxError,
    UnhandledResponseError,
)
from common.models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    ResourceNotFoundError,
    ResourceVersionNotProvided,
)
from controller.fhir_api_exception_handler import fhir_api_exception_handler


class TestFhirApiExceptionHandler(unittest.TestCase):
    def setUp(self):
        self.logger_patcher = patch("controller.fhir_api_exception_handler.logger")
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_exception_handler_does_nothing_when_no_exception_occurs(self):
        """Test that when the wrapped function returns successfully then the wrapper does nothing"""

        @fhir_api_exception_handler
        def dummy_func():
            return "Hello World"

        self.mock_logger.exception.assert_not_called()
        self.assertEqual(dummy_func(), "Hello World")

    def test_exception_handler_handles_custom_exception_and_returns_fhir_response(self):
        """Test that custom exceptions are handled by the wrapper and a valid response is returned to the client"""
        test_cases = [
            (
                InconsistentResourceVersion("Resource versions do not match"),
                400,
                "invariant",
                "Resource versions do not match",
            ),
            (
                InconsistentIdError("123"),
                400,
                "invariant",
                "Validation errors: The provided immunization id:123 doesn't match with the content of the request body",
            ),
            (InconsistentIdentifierError("Identifiers do not match"), 400, "invariant", "Identifiers do not match"),
            (InvalidJsonError("Invalid JSON provided"), 400, "invalid", "Invalid JSON provided"),
            (CustomValidationError("This field was invalid"), 400, "invariant", "This field was invalid"),
            (
                ResourceVersionNotProvided(resource_type="Immunization"),
                400,
                "invariant",
                "Validation errors: Immunization resource version not specified in the request headers",
            ),
            (
                InvalidResourceVersion(resource_version="badVersion"),
                400,
                "invariant",
                "Validation errors: Immunization resource version:badVersion in the request headers is invalid.",
            ),
            (UnauthorizedError(), 403, "forbidden", "Unauthorized request"),
            (
                UnauthorizedVaxError(),
                403,
                "forbidden",
                "Unauthorized request for vaccine type",
            ),
            (
                ResourceNotFoundError(resource_type="Immunization", resource_id="123"),
                404,
                "not-found",
                "Immunization resource does not exist. ID: 123",
            ),
            (
                IdentifierDuplicationError("system#id"),
                422,
                "duplicate",
                "The provided identifier: system#id is duplicated",
            ),
            (
                UnhandledResponseError(message="Critical error", response={"outcome": "critical error"}),
                500,
                "exception",
                "Critical error\n{'outcome': 'critical error'}",
            ),
        ]

        for error, expected_status, expected_code, expected_message in test_cases:
            with self.subTest(msg=f"Test {error.__class__.__name__}"):

                @fhir_api_exception_handler
                def dummy_func(e=error):
                    raise e

                response = dummy_func()

                self.mock_logger.exception.assert_not_called()

                operation_outcome = json.loads(response["body"])
                self.assertEqual(response["statusCode"], expected_status)
                self.assertEqual(operation_outcome["resourceType"], "OperationOutcome")
                self.assertEqual(operation_outcome["issue"][0]["code"], expected_code)
                self.assertEqual(operation_outcome["issue"][0]["diagnostics"], expected_message)

    def test_exception_handler_logs_exception_when_unexpected_error_occurs(self):
        """Test that when an unexpected exception occurs the exception is logged and an appropriate response is
        returned"""

        @fhir_api_exception_handler
        def dummy_func():
            raise Exception("Something went very wrong")

        response = dummy_func()

        self.mock_logger.exception.assert_called_once_with("Unhandled exception")

        operation_outcome = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(operation_outcome["resourceType"], "OperationOutcome")
        self.assertEqual(operation_outcome["issue"][0]["code"], "exception")
        self.assertEqual(
            operation_outcome["issue"][0]["diagnostics"],
            "Unable to process request. Issue may be transient.",
        )
