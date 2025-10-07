import json
import unittest
from unittest.mock import create_autospec, patch

from create_imms_handler import create_immunization
from controller.fhir_controller import FhirController
from models.errors import Severity, Code, create_operation_outcome
from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE


class TestCreateImmunizationById(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_create_immunization(self):
        """it should create Immunization"""
        lambda_event = {"aws": "event"}
        exp_res = {"a-key": "a-value"}

        self.controller.create_immunization.return_value = exp_res

        # When
        act_res = create_immunization(lambda_event, self.controller)

        # Then
        self.controller.create_immunization.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_create_handle_exception(self):
        """unhandled exceptions should result in 500"""
        lambda_event = {"aws": "event"}
        error_msg = "an unhandled error"
        self.controller.create_immunization.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(
            resource_id=None,
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )

        # When
        act_res = create_immunization(lambda_event, self.controller)

        # Then
        act_body = json.loads(act_res["body"])
        act_body["id"] = None

        self.assertDictEqual(act_body, exp_error)
        self.assertEqual(act_res["statusCode"], 500)
