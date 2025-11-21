import unittest
from unittest.mock import create_autospec, patch

from controller.fhir_controller import FhirController
from create_imms_handler import create_immunization


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
