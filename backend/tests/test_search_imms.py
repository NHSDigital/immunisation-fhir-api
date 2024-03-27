import json
import unittest
from unittest.mock import create_autospec

from fhir_controller import FhirController
from models.errors import Severity, Code, create_operation_outcome
from search_imms_handler import search_imms


class TestSearchImmunizations(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)

    def test_search_immunizations(self):
        """it should return a list of Immunizations"""
        lambda_event = {"pathParameters": {"id": "an-id",
                                           "-nhsNumber": "9693632109"}}
        exp_res = {"a-key": "a-value"}

        self.controller.search_immunizations.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.search_immunizations.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_handle_exception(self):
        """unhandled exceptions should result in 500"""
        lambda_event = {"pathParameters": {"id": "an-id",
                                           "-nhsNumber": "9693632109"}}
        error_msg = "an unhandled error"
        self.controller.search_immunizations.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(resource_id=None, severity=Severity.error,
                                             code=Code.server_error,
                                             diagnostics=error_msg)

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        act_body = json.loads(act_res["body"])
        act_body["id"] = None

        self.assertDictEqual(act_body, exp_error)
        self.assertEqual(act_res["statusCode"], 500)
