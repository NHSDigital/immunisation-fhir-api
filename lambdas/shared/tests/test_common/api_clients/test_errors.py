import unittest

import src.common.api_clients.errors as errors


class TestErrors(unittest.TestCase):
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

    def test_errors_forbidden_error(self):
        """Test correct operation of ForbiddenError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.ForbiddenError) as context:
            raise errors.ForbiddenError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), "Forbidden")

    def test_errors_resource_not_found_error(self):
        """Test correct operation of ResourceNotFoundError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.ResourceNotFoundError) as context:
            raise errors.ResourceNotFoundError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.not_found)

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
        self.assertEqual(issue.get("code"), errors.Code.exception)
        self.assertEqual(issue.get("diagnostics"), f"{test_message}\n{test_response}")

    def assert_response_message(self, context, test_response, test_message):
        """Helper method to assert response and message attributes"""
        self.assertEqual(context.exception.response, test_response)
        self.assertEqual(context.exception.message, test_message)

    def assert_operation_outcome(self, outcome):
        """Helper method to assert operation outcome structure"""
        self.assertEqual(outcome.get("resourceType"), "OperationOutcome")
        self.assertIsNotNone(outcome.get("id"))
        self.assertIsNotNone(outcome.get("meta"))
        self.assertIsNotNone(outcome.get("issue"))
        self.assertEqual(len(outcome.get("issue")), 1)
