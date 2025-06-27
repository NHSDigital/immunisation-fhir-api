import json
import unittest
from unittest.mock import create_autospec, patch

from fhir_controller import FhirController
from models.errors import Severity, Code, create_operation_outcome
from update_imms_handler import update_imms
from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE


class TestUpdateImmunizations(unittest.TestCase):
    def setUp(self):
        # self.controller = create_autospec(FhirController)
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()
        # patch FhirController
        self.controller = create_autospec(FhirController)
        self.controller.update_immunization = FhirController.update_immunization        

        

    def tearDown(self):
        self.logger_exception_patcher.stop()


    def test_update_immunization(self):
        """it should call service update method"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        exp_res = {"a-key": "a-value"}

        self.controller.update_immunization.return_value = exp_res

        # When
        act_res = update_imms(lambda_event, self.controller)

        # Then
        self.controller.update_immunization.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    @patch("update_imms_handler.FhirController.create_response")
    def test_update_imms_exception(self, mock_create_response):
        """unhandled exceptions should result in 500"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        error_msg = "an unhandled error"
        self.controller.update_immunization.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(
            resource_id=None,
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )
        mock_response = "controller-response-error"
        mock_create_response.return_value = mock_response

        # When
        act_res = update_imms(lambda_event, self.controller)

        # Then
        # check parameters used to call create_response
        args, kwargs = mock_create_response.call_args
        self.assertEqual(args[0], 500)
        issue = args[1]["issue"][0]
        severity = issue["severity"]
        code = issue["code"]
        diagnostics = issue["diagnostics"]
        self.assertEqual(severity, "error")
        self.assertEqual(code, "exception")
        self.assertEqual(diagnostics, GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE)
        self.assertEqual(act_res, mock_response)

        

    def test_update_imms_with_duplicated_identifier_returns_error(self):
        """Should return an IdentifierDuplication error"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        error_msg = {
            "statusCode": 422,
            "headers": {"Content-Type": "application/fhir+json"},
            "body": '{"resourceType": "OperationOutcome", "id": "5c132d8a-a928-4e0e-8792-0c6456e625c2", "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]}, "issue": [{"severity": "error", "code": "exception", "details": {"coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes","code": "DUPLICATE"}]}, "diagnostics": "The provided identifier: id-id is duplicated"}]}',
        }
        self.controller.update_immunization.return_value = error_msg

        act_res = update_imms(lambda_event, self.controller)

        # Then
        self.controller.update_immunization.assert_called_once_with(lambda_event)
        self.assertEqual(act_res["statusCode"], 422)
        self.assertDictEqual(act_res, error_msg)
