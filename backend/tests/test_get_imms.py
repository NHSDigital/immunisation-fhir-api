import unittest
from unittest.mock import create_autospec

from controller.fhir_controller import FhirController
from get_imms_handler import get_immunization_by_id



class TestGetImmunisationById(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)

    def test_get_immunization_by_id(self):
        """it should return Immunization by id"""
        lambda_event = {"headers": {"id": "an-id"}, "pathParameters": {"id": "an-id"}}
        exp_res = {"a-key": "a-value"}

        self.controller.get_immunization_by_id.return_value = exp_res

        # When
        act_res = get_immunization_by_id(lambda_event, self.controller)

        # Then
        self.controller.get_immunization_by_id.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)
