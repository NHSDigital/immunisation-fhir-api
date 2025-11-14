import unittest
from unittest.mock import patch

import models.errors as errors
from models.errors import Code, Severity, create_operation_outcome


class TestApiErrors(unittest.TestCase):
    def test_error_to_uk_core2(self):
        code = Code.not_found

        severity = Severity.error
        diag = "a-diagnostic"
        error_id = "a-id"

        error = create_operation_outcome(resource_id=error_id, severity=severity, code=code, diagnostics=diag)

        issue = error["issue"][0]
        self.assertEqual(error["id"], error_id)
        self.assertEqual(issue["code"], "not-found")
        self.assertEqual(issue["severity"], "error")
        self.assertEqual(issue["diagnostics"], diag)


class TestErrors(unittest.TestCase):
    def setUp(self):
        TEST_UUID = "01234567-89ab-cdef-0123-4567890abcde"
        # Patch uuid4
        self.uuid4_patch = patch("uuid.uuid4", return_value=TEST_UUID)
        self.mock_uuid4 = self.uuid4_patch.start()
        self.addCleanup(self.uuid4_patch.stop)

    def assert_response_message(self, context, response, message):
        self.assertEqual(context.exception.response, response)
        self.assertEqual(context.exception.message, message)

    def assert_resource_type_and_id(self, context, resource_type, resource_id):
        self.assertEqual(context.exception.resource_type, resource_type)
        self.assertEqual(context.exception.resource_id, resource_id)

    def assert_operation_outcome(self, outcome):
        self.assertEqual(outcome.get("resourceType"), "OperationOutcome")

    def test_errors_unauthorized_error(self):
        """Test correct operation of UnauthorizedError"""

        with self.assertRaises(errors.UnauthorizedError) as context:
            raise errors.UnauthorizedError()

        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), "Unauthorized request")

    def test_errors_unauthorized_vax_error(self):
        """Test correct operation of UnauthorizedVaxError"""

        with self.assertRaises(errors.UnauthorizedVaxError) as context:
            raise errors.UnauthorizedVaxError()

        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), "Unauthorized request for vaccine type")

    def test_errors_resource_version_not_provided(self):
        """Test correct operation of ResourceVersionNotProvided"""
        test_resource_type = "test_resource_type"

        with self.assertRaises(errors.ResourceVersionNotProvidedError) as context:
            raise errors.ResourceVersionNotProvidedError(test_resource_type)
        self.assertEqual(context.exception.resource_type, test_resource_type)
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invariant)
        self.assertEqual(
            issue.get("diagnostics"),
            f"Validation errors: {test_resource_type} resource version not specified in the request headers",
        )

    def test_errors_parameter_exception(self):
        """Test correct operation of ParameterException"""
        test_message = "test_message"

        with self.assertRaises(errors.ParameterExceptionError) as context:
            raise errors.ParameterExceptionError(test_message)
        self.assertEqual(context.exception.message, test_message)
        self.assertEqual(str(context.exception), test_message)

    def test_errors_invalid_immunization_id(self):
        """Test correct operation of InvalidImmunizationId"""

        with self.assertRaises(errors.InvalidImmunizationIdError) as context:
            raise errors.InvalidImmunizationIdError()

        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invalid)
        self.assertEqual(
            issue.get("diagnostics"),
            "Validation errors: the provided event ID is either missing or not in the expected format.",
        )

    def test_errors_invalid_resource_version(self):
        """Test correct operation of InvalidResourceVersion"""
        test_resource_version = "test_resource_version"

        with self.assertRaises(errors.InvalidResourceVersionError) as context:
            raise errors.InvalidResourceVersionError(test_resource_version)
        self.assertEqual(context.exception.resource_version, test_resource_version)
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invariant)
        self.assertEqual(
            issue.get("diagnostics"),
            f"Validation errors: Immunization resource version:{test_resource_version} in the request headers is invalid.",
        )

    def test_errors_inconsistent_id_error(self):
        """Test correct operation of InconsistentIdError"""
        test_imms_id = "test_imms_id"

        with self.assertRaises(errors.InconsistentIdError) as context:
            raise errors.InconsistentIdError(test_imms_id)
        self.assertEqual(context.exception.imms_id, test_imms_id)
        self.assertEqual(
            str(context.exception),
            f"Validation errors: The provided immunization id:{test_imms_id} doesn't match with the content of the request body",
        )
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invariant)
        self.assertEqual(
            issue.get("diagnostics"),
            f"Validation errors: The provided immunization id:{test_imms_id} doesn't match with the content of the request body",
        )

    def test_errors_invalid_json_error(self):
        """Test correct operation of InvalidJsonError"""
        test_message = "test_message"

        with self.assertRaises(errors.InvalidJsonError) as context:
            raise errors.InvalidJsonError(test_message)
        self.assertEqual(context.exception.message, test_message)

        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invalid)
        self.assertEqual(issue.get("diagnostics"), test_message)

    def test_errors_unhandled_response_error(self):
        """Test correct operation of UnhandledResponseError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.UnhandledResponseError) as context:
            raise errors.UnhandledResponseError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.server_error)
        self.assertEqual(issue.get("diagnostics"), f"{test_message}\n{test_response}")
