import unittest
from unittest.mock import create_autospec, patch

from controller.fhir_controller import FhirController
from delete_imms_handler import delete_immunization


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
