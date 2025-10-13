import unittest
from unittest.mock import patch
import src.common.models.errors as errors


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

    def test_errors_unauthorized_vax_error(self):
        """Test correct operation of UnauthorizedVaxError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.UnauthorizedVaxError) as context:
            raise errors.UnauthorizedVaxError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), "Unauthorized request for vaccine type")

    def test_errors_unauthorized_vax_on_record_error(self):
        """Test correct operation of UnauthorizedVaxOnRecordError"""
        test_response = "test_response"
        test_message = "test_message"

        with self.assertRaises(errors.UnauthorizedVaxOnRecordError) as context:
            raise errors.UnauthorizedVaxOnRecordError(test_response, test_message)
        self.assert_response_message(context, test_response, test_message)
        self.assertEqual(str(context.exception), f"{test_message}\n{test_response}")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(
            issue.get("diagnostics"),
            "Unauthorized request for vaccine type present in the stored immunization resource",
        )

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

    def test_errors_validation_error(self):
        """Test correct operation of ValidationError"""
        with self.assertRaises(errors.ValidationError) as context:
            raise errors.ValidationError()
        outcome = context.exception.to_operation_outcome()
        self.assertIsNone(outcome)

    def test_errors_invalid_patient_id(self):
        """Test correct operation of InvalidPatientId"""
        test_patient_identifier = "test_patient_identifier"

        with self.assertRaises(errors.InvalidPatientId) as context:
            raise errors.InvalidPatientId(test_patient_identifier)
        self.assertEqual(context.exception.patient_identifier, test_patient_identifier)
        self.assertEqual(
            str(context.exception),
            f"NHS Number: {test_patient_identifier} is invalid or it doesn't exist.",
        )
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.exception)
        self.assertEqual(
            issue.get("diagnostics"),
            f"NHS Number: {test_patient_identifier} is invalid or it doesn't exist.",
        )

    def test_errors_inconsistent_id_error(self):
        """Test correct operation of InconsistentIdError"""
        test_imms_id = "test_imms_id"

        with self.assertRaises(errors.InconsistentIdError) as context:
            raise errors.InconsistentIdError(test_imms_id)
        self.assertEqual(context.exception.imms_id, test_imms_id)
        self.assertEqual(
            str(context.exception),
            f"The provided id:{test_imms_id} doesn't match with the content of the message",
        )
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.exception)
        self.assertEqual(
            issue.get("diagnostics"),
            f"The provided id:{test_imms_id} doesn't match with the content of the message",
        )

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

    def test_errors_parameter_exception(self):
        """Test correct operation of ParameterException"""
        test_message = "test_message"

        with self.assertRaises(errors.ParameterException) as context:
            raise errors.ParameterException(test_message)
        self.assertEqual(context.exception.message, test_message)
        self.assertEqual(str(context.exception), test_message)

    def test_errors_unauthorized_system_error(self):
        """Test correct operation of UnauthorizedSystemError"""
        test_message = "test_message"

        with self.assertRaises(errors.UnauthorizedSystemError) as context:
            raise errors.UnauthorizedSystemError(test_message)
        self.assertEqual(context.exception.message, test_message)
        self.assertEqual(str(context.exception), test_message)
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), test_message)

    def test_errors_unauthorized_system_error_no_message(self):
        """Test correct operation of UnauthorizedSystemError with no message"""

        with self.assertRaises(errors.UnauthorizedSystemError) as context:
            raise errors.UnauthorizedSystemError()
        self.assertEqual(context.exception.message, "Unauthorized system")
        self.assertEqual(str(context.exception), "Unauthorized system")
        outcome = context.exception.to_operation_outcome()
        self.assert_operation_outcome(outcome)
        issue = outcome.get("issue")[0]
        self.assertEqual(issue.get("severity"), errors.Severity.error)
        self.assertEqual(issue.get("code"), errors.Code.forbidden)
        self.assertEqual(issue.get("diagnostics"), "Unauthorized system")

    def test_errors_message_not_successful_error(self):
        """Test correct operation of MessageNotSuccessfulError"""
        test_message = "test_message"

        with self.assertRaises(errors.MessageNotSuccessfulError) as context:
            raise errors.MessageNotSuccessfulError(test_message)
        self.assertEqual(str(context.exception.message), test_message)

    def test_errors_message_not_successful_error_no_message(self):
        """Test correct operation of MessageNotSuccessfulError with no message"""

        with self.assertRaises(errors.MessageNotSuccessfulError) as context:
            raise errors.MessageNotSuccessfulError()
        self.assertIsNone(context.exception.message)

    def test_errors_record_processor_error(self):
        """Test correct operation of RecordProcessorError"""
        test_diagnostics = {"test_diagnostic": "test_value"}

        with self.assertRaises(errors.RecordProcessorError) as context:
            raise errors.RecordProcessorError(test_diagnostics)
        self.assertEqual(context.exception.diagnostics_dictionary, test_diagnostics)
