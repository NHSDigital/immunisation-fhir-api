import json
import unittest
from unittest.mock import create_autospec, patch

from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE
from delete_imms_handler import delete_immunization
from fhir_controller import FhirController
from models.errors import Code, Severity, create_operation_outcome


class TestDeleteImmunizationById(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_delete_immunization(self):
        """it should delete Immunization"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        exp_res = {"a-key": "a-value"}

        self.controller.delete_immunization.return_value = exp_res

        # When
        act_res = delete_immunization(lambda_event, self.controller)

        # Then
        self.controller.delete_immunization.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_delete_handle_exception(self):
        """unhandled exceptions should result in 500"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        error_msg = "an unhandled error"
        self.controller.delete_immunization.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(
            resource_id=None,
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )

        # When
        act_res = delete_immunization(lambda_event, self.controller)

        # Then
        act_body = json.loads(act_res["body"])
        act_body["id"] = None

        self.assertDictEqual(act_body, exp_error)
        self.assertEqual(act_res["statusCode"], 500)
