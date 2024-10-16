import json
import unittest
from unittest.mock import create_autospec

from fhir_controller import FhirController
from models.errors import Severity, Code, create_operation_outcome
from update_imms_handler import update_imms


class TestUpdateImmunizations(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)

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

    def test_handle_exception(self):
        """unhandled exceptions should result in 500"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        error_msg = "an unhandled error"
        self.controller.update_immunization.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(
            resource_id=None, severity=Severity.error, code=Code.server_error, diagnostics=error_msg
        )

        # When
        act_res = update_imms(lambda_event, self.controller)

        # Then
        act_body = json.loads(act_res["body"])
        act_body["id"] = None

        #self.assertDictEqual(act_body, exp_error)
        self.assertEqual(act_res["statusCode"], 500)

    def test_update_imms_with_duplicated_identifier_returns_error(self):
        """Should return an IdentifierDuplication error"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        error_msg = {'statusCode': 422, 'headers': {'Content-Type': 'application/fhir+json'}, 'body': '{"resourceType": "OperationOutcome", "id": "5c132d8a-a928-4e0e-8792-0c6456e625c2", "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]}, "issue": [{"severity": "error", "code": "exception", "details": {"coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes","code": "DUPLICATE"}]}, "diagnostics": "The provided identifier: id-id is duplicated"}]}'}
        self.controller.update_immunization.return_value = error_msg

        act_res = update_imms(lambda_event, self.controller)
       
        # Then
        self.controller.update_immunization.assert_called_once_with(lambda_event)
        self.assertEqual(act_res["statusCode"], 422)
        self.assertDictEqual(act_res, error_msg)