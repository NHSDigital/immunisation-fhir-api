import unittest
from unittest.mock import patch

import common.models.errors as errors


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

    def test_errors_mandatory_error(self):
        """Test correct operation of MandatoryError"""
        test_message = "test_message"

        with self.assertRaises(errors.MandatoryError) as context:
            raise errors.MandatoryError(test_message)
        self.assertEqual(str(context.exception.message), test_message)

    def test_errors_mandatory_error_no_message(self):
        """Test correct operation of MandatoryError with no message"""

        with self.assertRaises(errors.MandatoryError) as context:
            raise errors.MandatoryError()
        self.assertIsNone(context.exception.message)

    def test_errors_resource_not_found_error(self):
        """Test correct operation of ResourceNotFoundError"""
        test_resource_type = "test_resource_type"
        test_resource_id = "test_resource_id"

        with self.assertRaises(errors.ResourceNotFoundError) as context:
            raise errors.ResourceNotFoundError(test_resource_type, test_resource_id)
        self.assert_resource_type_and_id(context, test_resource_type, test_resource_id)
        self.assertEqual(
            str(context.exception),
            f"{test_resource_type} resource does not exist. ID: {test_resource_id}",
        )
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.not_found)
        self.assertEqual(
            issue.get("diagnostics"),
            f"{test_resource_type} resource does not exist. ID: {test_resource_id}",
        )

    def test_errors_resource_found_error(self):
        """Test correct operation of ResourceFoundError"""
        test_resource_type = "test_resource_type"
        test_resource_id = "test_resource_id"

        with self.assertRaises(errors.ResourceFoundError) as context:
            raise errors.ResourceFoundError(test_resource_type, test_resource_id)
        self.assert_resource_type_and_id(context, test_resource_type, test_resource_id)
        self.assertEqual(
            str(context.exception),
            f"{test_resource_type} resource does exist. ID: {test_resource_id}",
        )
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.not_found)
        self.assertEqual(
            issue.get("diagnostics"),
            f"{test_resource_type} resource does exist. ID: {test_resource_id}",
        )

    def test_errors_inconsistent_identifier_error(self):
        """Test correct operation of InconsistentIdentifierError"""
        test_imms_id = "test_imms_id"

        with self.assertRaises(errors.InconsistentIdentifierError) as context:
            raise errors.InconsistentIdentifierError(test_imms_id)
        self.assertEqual(context.exception.msg, test_imms_id)

        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invariant)
        self.assertEqual(issue.get("diagnostics"), test_imms_id)

    def test_errors_inconsistent_resource_version(self):
        """Test correct operation of InconsistentResourceVersion"""
        test_message = "test_message"

        with self.assertRaises(errors.InconsistentResourceVersion) as context:
            raise errors.InconsistentResourceVersion(test_message)
        self.assertEqual(context.exception.message, test_message)

        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invariant)
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
        self.assertEqual(issue.get("code"), errors.Code.exception)
        self.assertEqual(issue.get("diagnostics"), f"{test_message}\n{test_response}")

    def test_errors_api_validation_error(self):
        """Test correct operation of ApiValidationError"""
        with self.assertRaises(errors.ApiValidationError) as context:
            raise errors.ApiValidationError()
        outcome = context.exception.to_operation_outcome()
        self.assertIsNone(outcome)

    def test_errors_custom_validation_error(self):
        """Test correct operation of CustomValidationError"""
        test_message = "test_message"

        with self.assertRaises(errors.CustomValidationError) as context:
            raise errors.CustomValidationError(test_message)
        self.assertEqual(context.exception.message, test_message)
        self.assertEqual(str(context.exception), test_message)
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.invariant)
        self.assertEqual(issue.get("diagnostics"), test_message)

    def test_errors_identifier_duplication_error(self):
        """Test correct operation of IdentifierDuplicationError"""
        test_identifier = "test_identifier"

        with self.assertRaises(errors.IdentifierDuplicationError) as context:
            raise errors.IdentifierDuplicationError(test_identifier)
        self.assertEqual(context.exception.identifier, test_identifier)
        self.assertEqual(
            str(context.exception),
            f"The provided identifier: {test_identifier} is duplicated",
        )
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.duplicate)
        self.assertEqual(
            issue.get("diagnostics"),
            f"The provided identifier: {test_identifier} is duplicated",
        )
