import json
import unittest
from unittest.mock import create_autospec, patch

from fhir_controller import FhirController
from models.errors import Severity, Code, create_operation_outcome
from search_imms_handler import search_imms
from pathlib import Path
from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE

script_location = Path(__file__).absolute().parent


class TestSearchImmunizations(unittest.TestCase):
    def setUp(self):
        self.controller = create_autospec(FhirController)
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_search_immunizations(self):
        """it should return a list of Immunizations"""
        lambda_event = {"pathParameters": {"id": "an-id"}, "body": None}
        exp_res = {"a-key": "a-value"}

        self.controller.search_immunizations.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.search_immunizations.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_to_get_imms_id(self):
        """it should return a list of Immunizations"""
        lambda_event = {
            "pathParameters": {"id": "an-id"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": None,
        }
        exp_res = {"a-key": "a-value"}

        self.controller.get_immunization_by_identifier.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.get_immunization_by_identifier.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_get_id_from_body(self):
        """it should return a list of Immunizations"""
        lambda_event = {
            "pathParameters": {"id": "an-id"},
            "body": "cGF0aWVudC5pZGVudGlmaWVyPWh0dHBzJTNBJTJGJTJGZmhpci5uaHMudWslMkZJZCUyRm5ocy1udW1iZXIlN0M5NjkzNjMyMTA5Ji1pbW11bml6YXRpb24udGFyZ2V0PUNPVklEMTkmX2luY2x1ZGU9SW1tdW5pemF0aW9uJTNBcGF0aWVudCZpbW11bml6YXRpb24uaWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJTdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50PWlkJTJDbWV0YSZpZD1z",
            "queryStringParameters": None,
        }
        exp_res = {"a-key": "a-value"}

        self.controller.get_immunization_by_identifier.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.get_immunization_by_identifier.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_get_id_from_body_passing_none(self):
        """it should enter search_immunizations as both the request params are none"""
        lambda_event = {"pathParameters": {"id": "an-id"}, "body": None, "queryStringParameters": None}
        exp_res = {"a-key": "a-value"}

        self.controller.search_immunizations.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.search_immunizations.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_get_id_from_body_element(self):
        """it should enter into  get_immunization_by_identifier  only _element paramter is present"""
        lambda_event = {
            "pathParameters": {"id": "an-id"},
            "body": "X2VsZW1lbnQ9aWQlMkNtZXRh",
            "queryStringParameters": None,
        }
        exp_res = {"a-key": "a-value"}

        self.controller.get_immunization_by_identifier.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.get_immunization_by_identifier.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_get_id_from_body_imms_identifer(self):
        """it should enter into  get_immunization_by_identifier  only immunization.identifier paramter is present"""
        lambda_event = {
            "pathParameters": {"id": "an-id"},
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aWQlMkNtZXRh",
            "queryStringParameters": None,
        }
        exp_res = {"a-key": "a-value"}

        self.controller.get_immunization_by_identifier.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.get_immunization_by_identifier.assert_called_once_with(lambda_event)
        self.assertDictEqual(exp_res, act_res)

    def test_search_immunizations_lambda_size_limit(self):
        """it should return 400 as search returned too many results."""
        lambda_event = {"pathParameters": {"id": "an-id"}, "body": None}
        request_file = script_location / "sample_data" / "sample_input_search_imms.json"
        with open(request_file) as f:
            exp_res = json.load(f)
        self.controller.search_immunizations.return_value = json.dumps(exp_res)

        self.controller.search_immunizations.return_value = exp_res

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        self.controller.search_immunizations.assert_called_once_with(lambda_event)
        self.assertEqual(act_res["statusCode"], 400)

    def test_handle_exception(self):
        """unhandled exceptions should result in 500"""
        lambda_event = {"pathParameters": {"id": "an-id"}}
        error_msg = "an unhandled error"
        self.controller.search_immunizations.side_effect = Exception(error_msg)

        exp_error = create_operation_outcome(
            resource_id=None,
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )

        # When
        act_res = search_imms(lambda_event, self.controller)

        # Then
        act_body = json.loads(act_res["body"])
        # act_body["id"] = None

        self.assertEqual(exp_error["issue"][0]["code"], act_body["issue"][0]["code"])
        self.assertEqual(exp_error["issue"][0]["severity"], act_body["issue"][0]["severity"])
        self.assertEqual(act_res["statusCode"], 500)
