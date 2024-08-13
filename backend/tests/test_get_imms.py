import json
import unittest
from unittest.mock import create_autospec

from fhir_controller import FhirController
from get_imms_handler import get_immunization_by_id
from models.errors import Severity, Code, create_operation_outcome


class TestGetImmunisationById(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)

    def test_get_immunization_by_id(self):
        """it should return Immunization by id"""
        lambda_event = {'headers': {'id': 'an-id'},"pathParameters": {"id": "an-id"}}
        exp_res = {"a-key": "a-value"}

        self.controller.get_immunization_by_id.return_value = exp_res

        # When
        act_res = get_immunization_by_id(lambda_event, self.controller)

        # Then
        self.controller.get_immunization_by_id.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_handle_exception(self):
        """unhandled exceptions should result in 500"""
        lambda_event = {'headers': {'id': 'an-id'},"pathParameters": {"id": "an-id"}}
        error_msg = "an unhandled error"
        self.controller.get_immunization_by_id.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(resource_id=None, severity=Severity.error,
                                             code=Code.server_error,
                                             diagnostics=error_msg)

        # When
        act_res = get_immunization_by_id(lambda_event, self.controller)

        # Then
        act_body = json.loads(act_res["body"])
        act_body["id"] = None

        self.assertDictEqual(act_body, exp_error)
        self.assertEqual(act_res["statusCode"], 500)
