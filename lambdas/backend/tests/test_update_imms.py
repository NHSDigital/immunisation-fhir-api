import unittest
from unittest.mock import create_autospec

from controller.fhir_controller import FhirController
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
