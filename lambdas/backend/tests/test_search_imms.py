import unittest
from unittest.mock import create_autospec

from controller.fhir_controller import FhirController
from search_imms_handler import search_imms


class TestSearchImmunizations(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)

    def test_search_immunizations_calls_controller_with_correct_params_when_client_using_get_endpoint(self):
        """it should return a list of Immunizations"""
        lambda_event = {
            "multiValueQueryStringParameters": {
                "identifier": ["https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184"],
                "_elements": ["id,meta"],
            },
            "path": "/Immunization",
            "httpMethod": "GET",
            "body": None,
        }
        exp_res = {"a-key": "a-value"}

        self.controller.search_immunizations.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.search_immunizations.assert_called_once_with(lambda_event, is_post_endpoint_req=False)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_calls_controller_with_correct_params_when_client_using_post_endpoint(self):
        """it should return a list of Immunizations"""
        lambda_event = {
            "multiValueQueryStringParameters": {},
            "path": "/Immunization/_search",
            "httpMethod": "POST",
            "body": "some+payload",
        }
        exp_res = {"a-key": "a-value"}

        self.controller.search_immunizations.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.search_immunizations.assert_called_once_with(lambda_event, is_post_endpoint_req=True)
        self.assertDictEqual(exp_res, act_res)
