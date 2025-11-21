import unittest
from unittest.mock import patch

import models.errors as errors


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

    def assert_operation_outcome(self, outcome):
        self.assertEqual(outcome.get("resourceType"), "OperationOutcome")

    def test_errors_unauthorized_error(self):
        """Test correct operation of UnauthorizedError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.UnauthorizedError) as context:
            raise errors.UnauthorizedError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), "Unauthorized request")

    def test_errors_token_validation_error(self):
        """Test correct operation of TokenValidationError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.TokenValidationError) as context:
            raise errors.TokenValidationError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invalid)
        self.assertEqual(issue.get("diagnostics"), "Missing/Invalid Token")

    def test_errors_conflict_error(self):
        """Test correct operation of ConflictError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.ConflictError) as context:
            raise errors.ConflictError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.duplicate)
        self.assertEqual(issue.get("diagnostics"), "Conflict")

    def test_errors_bad_request_error(self):
        """Test correct operation of BadRequestError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.BadRequestError) as context:
            raise errors.BadRequestError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.incomplete)
        self.assertEqual(issue.get("diagnostics"), f"{test_message}\n{test_response}")

    def test_errors_server_error(self):
        """Test correct operation of ServerError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.ServerError) as context:
            raise errors.ServerError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.server_error)
        self.assertEqual(issue.get("diagnostics"), f"{test_message}\n{test_response}")
