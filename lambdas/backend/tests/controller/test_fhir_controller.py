import base64
import json
import unittest
import urllib
import urllib.parse
import uuid
from unittest.mock import ANY, Mock, create_autospec, patch
from urllib.parse import urlencode

from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.immunization import Immunization

from common.models.errors import (
    CustomValidationError,
    ResourceNotFoundError,
)
from controller.aws_apig_response_utils import create_response
from controller.fhir_controller import FhirController
from models.errors import (
    ParameterExceptionError,
    UnauthorizedVaxError,
    UnhandledResponseError,
)
from parameter_parser import patient_identifier_system, process_search_params
from repository.fhir_repository import ImmunizationRepository
from service.fhir_service import FhirService
from test_common.testing_utils.generic_utils import load_json_data
from test_common.testing_utils.immunization_utils import create_covid_immunization


class TestFhirControllerBase(unittest.TestCase):
    """Base class for all tests to set up common fixtures"""

    def setUp(self):
        super().setUp()
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("parameter_parser.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.redis_getter_patcher.stop()
        self.logger_info_patcher.stop()
        super().tearDown()


class TestFhirController(TestFhirControllerBase):
    def setUp(self):
        super().setUp()
        self.service = create_autospec(FhirService)
        self.repository = create_autospec(ImmunizationRepository)
        self.controller = FhirController(self.service)

    def test_create_response(self):
        """it should return application/fhir+json with correct status code"""
        body = {"message": "a body"}
        res = create_response(42, body)
        headers = res["headers"]

        self.assertEqual(res["statusCode"], 42)
        self.assertDictEqual(
            headers,
            {
                "Content-Type": "application/fhir+json",
            },
        )
        self.assertDictEqual(json.loads(res["body"]), body)

    def test_no_body_no_header(self):
        res = create_response(42)
        self.assertEqual(res["statusCode"], 42)
        self.assertDictEqual(res["headers"], {})
        self.assertTrue("body" not in res)


class TestFhirControllerGetImmunizationByIdentifier(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()

    def test_get_imms_by_identifer(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id,meta",
            },
            "body": None,
        }
        identifier = lambda_event.get("queryStringParameters", {}).get("identifier")
        _element = lambda_event.get("queryStringParameters", {}).get("_elements")

        identifiers = identifier.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(identifiers, "test", identifier, _element)

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    def test_get_imms_by_identifer_header_missing(self):
        """it should return Immunization Id if it exists"""
        # Given
        lambda_event = {
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id,meta",
            },
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(response["statusCode"], 403)

    def test_not_found_for_identifier(self):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/Immunization?immunization.target=COVID&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7C1345678940",
                }
            ],
            "entry": [],
            "total": 0,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id,meta",
                "SupplierSystem": "test",
            },
            "body": None,
        }
        identifier = lambda_event.get("queryStringParameters", {}).get("identifier")
        _element = lambda_event.get("queryStringParameters", {}).get("_elements")

        imms = identifier.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(imms, "test", identifier, _element)

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        self.assertEqual(body["entry"], [])
        self.assertEqual(body["total"], 0)

    def test_get_imms_by_identifer_patient_identifier_and_element_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "patient.identifier": "test",
                "_elements": "id,meta",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_imms_by_identifer_both_body_and_query_params_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "patient.identifier": "test",
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id,meta",
            },
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD1pZCUyQ21ldGEmaWQ9cw==",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_imms_by_identifer_both_identifier_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "patient.identifier": "test",
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id,meta",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_imms_by_identifer_invalid_element(self):
        """it should return 400 as it contain invalid _element if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id,meta,name",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_validate_immunization_identifier_is_empty(self):
        """it should return 400 as identifierSystem is missing"""
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {"identifier": "", "_elements": "id"},
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_immunization_identifier_in_invalid_format(self):
        """it should return 400 as identifierSystem is missing"""
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "identifier must be in the format of identifier.system|identifier.value e.g. http://pinnacle.org/vaccs|2345-gh3s-r53h7-12ny",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vaccf10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id",
            },
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_immunization_identifier_having_whitespace(self):
        """it should return 400 as identifierSystem is missing"""
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vacc  |   f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id",
            },
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_imms_id_invalid_vaccinetype(self):
        """it should validate lambda's Immunization id"""
        # Given
        self.service.get_immunization_by_identifier.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_elements": "id",
            },
            "body": None,
        }
        identifier = lambda_event.get("queryStringParameters", {}).get("identifier")
        _element = lambda_event.get("queryStringParameters", {}).get("_elements")
        identifiers = identifier.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(identifiers, "test", identifier, _element)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")


class TestFhirControllerGetImmunizationByIdentifierPost(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)

    def set_up_lambda_event(self, body):
        """Helper to create and set up a lambda event with the given body"""
        return {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJTdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50cz1pZCUyQ21ldGEmaWQ9cw==",
        }

    def parse_lambda_body(self, lambda_event):
        """Helper to parse and decode lambda event body"""
        decoded_body = base64.b64decode(lambda_event["body"]).decode("utf-8")
        parsed_body = urllib.parse.parse_qs(decoded_body)
        immunization_identifier = parsed_body.get("identifier", "")
        converted_identifier = "".join(immunization_identifier)
        element = parsed_body.get("_elements", "")
        converted_element = "".join(element)
        identifiers = converted_identifier.replace("|", "#")
        return identifiers, converted_identifier, converted_element

    def test_get_imms_by_identifier(self):
        """It should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        body = "identifier=https://supplierABC/identifiers/vacc#f10b59b3-fc73-4616-99c9-9e882ab31184&_elements=id|meta"
        lambda_event = self.set_up_lambda_event(body)
        identifiers, converted_identifier, converted_element = self.parse_lambda_body(lambda_event)

        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "test", converted_identifier, converted_element
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    def test_not_found_for_identifier(self):
        """It should return not-found OperationOutcome if it doesn't exist"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/Immunization?immunization.target=COVID&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7C1345678940",
                }
            ],
            "entry": [],
            "total": 0,
        }
        body = "identifier=https://supplierABC/identifiers/vacc#f10b59b3-fc73-4616-99c9-9e882ab31184&_elements=id|meta"
        lambda_event = self.set_up_lambda_event(body)
        identifiers, converted_identifier, converted_element = self.parse_lambda_body(lambda_event)

        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "test", converted_identifier, converted_element
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        self.assertEqual(body["entry"], [])
        self.assertEqual(body["total"], 0)

    def test_get_imms_by_identifer_patient_identifier_and_element_present(self):
        """it should return 400 as its having invalid request"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "cGF0aWVudC5pZGVudGlmaWVyPWh0dHBzJTNBJTJGJTJGZmhpci5uaHMudWslMkZJZCUyRm5ocy1udW1iZXIlN0M5NjkzNjMyMTA5Jl9lbGVtZW50cz1pZCUyQ21ldGE=",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_imms_by_identifer_imms_identifier_and_element_not_present(self):
        """it should return 400 as its having invalid request"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJSAgN0NmMTBiNTliMy1mYzczLTQ2MTYtOTljOS05ZTg4MmFiMzExODQmX2VsZW1lbnRzPWlkJTJDbWV0YSZpZD1z",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_validate_immunization_element_is_empty(self):
        """it should return 400 as element is missing"""
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD0nJw==",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_immunization_identifier_is_invalid(self):
        """it should return 400 as identifierSystem is invalid"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYzdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50PWlkJTJDbWV0YSZpZD1z",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_get_imms_by_identifer_both_identifier_present(self):
        """it should return 400 as its having invalid request"""
        # Given
        # Given
        self.service.get_immunization_by_identifier.return_value = {
            "id": "test",
            "Version": 1,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "cGF0aWVudC5pZGVudGlmaWVyPWh0dHBzJTNBJTJGJTJGZmhpci5uaHMudWslMkZJZCUyRm5ocy1udW1iZXIlN0M5NjkzNjMyMTA5Ji1pbW11bml6YXRpb24udGFyZ2V0PUNPVklEMTkmX2luY2x1ZGU9SW1tdW5pemF0aW9uJTNBcGF0aWVudCZpZGVudGlmaWVyPWh0dHBzJTNBJTJGJTJGc3VwcGxpZXJBQkMlMkZpZGVudGlmaWVycyUyRnZhY2MlN0NmMTBiNTliMy1mYzczLTQ2MTYtOTljOS05ZTg4MmFiMzExODQmX2VsZW1lbnRzPWlkJTJDbWV0YSZpZD1z",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_imms_by_identifer_invalid_element(self):
        """it should return 400 as it contain invalid _element if it exists"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJTdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50cz1pZCUyQ21ldGElMkNuYW1l",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_validate_immunization_identifier_is_empty(self):
        """it should return 400 as identifierSystem is missing"""
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "identifier must be in the format of identifier.system|identifier.value e.g. http://pinnacle.org/vaccs|2345-gh3s-r53h7-12ny",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aWRlbnRpZmllcj0mX2VsZW1lbnRzPWlkJTJDbWV0YQ==",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_immunization_identifier_having_whitespace(self):
        """it should return 400 as whitespace in id"""
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "INVALID",
                            }
                        ]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJSAgN0NmMTBiNTliMy1mYzczLTQ2MTYtOTljOS05ZTg4MmFiMzExODQmX2VsZW1lbnRzPWlkJTJDbWV0YSZpZD1z",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_imms_id_invalid_vaccinetype(self):
        """it should validate lambda's Immunization id"""
        # Given
        self.service.get_immunization_by_identifier.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJTdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50cz1pZCUyQ21ldGEmaWQ9cw==",
        }
        decoded_body = base64.b64decode(lambda_event["body"]).decode("utf-8")
        # Parse the URL encoded body
        parsed_body = urllib.parse.parse_qs(decoded_body)

        immunization_identifier = parsed_body.get("identifier", "")
        converted_identifier = "".join(immunization_identifier)
        element = parsed_body.get("_elements", "")
        converted_element = "".join(element)

        identifiers = converted_identifier.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "test", converted_identifier, converted_element
        )

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")


class TestFhirControllerGetImmunizationById(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)

    def test_get_imms_by_id(self):
        """it should return Immunization resource if it exists"""
        # Given
        imms_id = "a-id"
        self.service.get_immunization_and_version_by_id.return_value = (
            Immunization.construct(),
            "1",
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.service.get_immunization_and_version_by_id.assert_called_once_with(imms_id, "test")

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Immunization")
        self.assertEqual(response["headers"]["E-Tag"], "1")

    def test_get_imms_by_id_returns_unauthorized_when_supplier_header_missing(self):
        """it should return Immunization resource if it exists"""
        # Given
        imms_id = "foo-123"
        lambda_event = {
            "headers": {"missing": "required supplier header"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.service.get_immunization_and_version_by_id.assert_not_called()

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_get_imms_by_id_unauthorised_vax_error(self):
        """it should return a 403 error is the service layer throws an UnauthorizedVaxError"""
        # Given
        imms_id = "a-id"
        self.service.get_immunization_and_version_by_id.side_effect = UnauthorizedVaxError
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")

    def test_not_found(self):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        imms_id = "a-non-existing-id"
        self.service.get_immunization_and_version_by_id.side_effect = ResourceNotFoundError(
            resource_type="Immunization", resource_id=imms_id
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)

        # Then
        self.service.get_immunization_and_version_by_id.assert_called_once_with(imms_id, "test")

        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    def test_validate_imms_id(self):
        """it should validate lambda's Immunization id"""
        invalid_id = {"pathParameters": {"id": "invalid %$ id"}}

        response = self.controller.get_immunization_by_id(invalid_id)

        self.assertEqual(self.service.get_immunization_and_version_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")


class TestCreateImmunization(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_create_immunization(self):
        """it should create Immunization and return resource's location"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_immunization(imms_id)
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        self.service.create_immunization.return_value = imms_id

        response = self.controller.create_immunization(aws_event)

        imms_obj = json.loads(aws_event["body"])
        self.service.create_immunization.assert_called_once_with(imms_obj, "Test")
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{imms_id}"))

    def test_create_immunization_returns_unauthorised_error_when_supplier_system_header_missing(self):
        """it should return unauthorized error"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_immunization(imms_id)
        aws_event = {"body": imms.json()}

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)

    def test_create_immunization_for_unauthorized(self):
        """it should return an unauthorized error when the service finds that user lacks permissions"""
        # Given
        imms_id = str(uuid.uuid4())
        imms = create_covid_immunization(imms_id)
        aws_event = {
            "headers": {
                "SupplierSystem": "test",
            },
            "body": imms.json(),
        }
        # Mock the create_immunization return value
        self.service.create_immunization.side_effect = UnauthorizedVaxError()

        # Execute the function under test
        response = self.controller.create_immunization(aws_event)

        # Assert the response
        self.assertEqual(response["statusCode"], 403)

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = '{foo: "bar"}'
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": bad_json,
        }

        response = self.controller.create_immunization(aws_event)
        self.assertEqual(self.service.get_immunization_and_version_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_custom_validation_error(self):
        """it should handle ValidationError when patient NHS Number is invalid"""
        # Given
        imms = Immunization.construct()
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        invalid_nhs_num = "a-bad-id"
        self.service.create_immunization.side_effect = CustomValidationError(
            f"{invalid_nhs_num} is not a valid NHS number"
        )

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue(invalid_nhs_num in body["issue"][0]["diagnostics"])

    def test_unhandled_error(self):
        """it should respond with 500 on UnhandledResponseError"""
        imms = Immunization.construct()
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        self.service.create_immunization.side_effect = UnhandledResponseError(response={}, message="a message")

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(500, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")


class TestUpdateImmunization(unittest.TestCase):
    mock_imms_id = "valid-id"
    mock_imms_payload = {"id": "valid-id"}

    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_update_immunization(self):
        """it should update Immunization"""
        # Given
        aws_event = {
            "headers": {"E-Tag": "1", "SupplierSystem": "Test"},
            "body": json.dumps(self.mock_imms_payload),
            "pathParameters": {"id": self.mock_imms_id},
        }
        self.service.update_immunization.return_value = 2
        response = self.controller.update_immunization(aws_event)

        self.service.update_immunization.assert_called_once_with(self.mock_imms_id, self.mock_imms_payload, "Test", 1)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["E-Tag"], 2)

    def test_update_immunization_etag_missing(self):
        """it should raise an error if the E-Tag header is missing"""
        # Given
        # E-Tag header missing from headers section
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": json.dumps(self.mock_imms_payload),
            "pathParameters": {"id": self.mock_imms_id},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Validation errors: Immunization resource version not specified in the request headers",
        )

    def test_update_immunization_returns_unauthorised_when_supplier_system_header_missing(self):
        """it should return a 403 error when the supplier system header is missing"""
        aws_event = {"body": {}, "header": {"missing": "supplier-system"}, "pathParameters": {"id": self.mock_imms_id}}

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(json.loads(response["body"])["issue"][0]["diagnostics"], "Unauthorized request")

    def test_update_immunization_returns_unauthorised_when_client_does_not_have_required_permissions(self):
        """it should return a 403 error when the service raises an UnauthorizedVaxError"""
        aws_event = {
            "headers": {"E-Tag": "1", "SupplierSystem": "Test"},
            "body": json.dumps(self.mock_imms_payload),
            "pathParameters": {"id": self.mock_imms_id},
        }
        self.service.update_immunization.side_effect = UnauthorizedVaxError()
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)

    def test_update_immunization_for_invalid_version_string(self):
        """it should not update Immunization"""
        # Given
        aws_event = {
            "headers": {"E-Tag": "ajjsajj", "SupplierSystem": "Test"},
            "body": json.dumps(self.mock_imms_payload),
            "pathParameters": {"id": self.mock_imms_id},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Validation errors: Immunization resource version:ajjsajj in the request headers is invalid.",
        )

    def test_update_immunization_for_invalid_version_negative_number(self):
        """it should not update Immunization"""
        # Given
        aws_event = {
            "headers": {"E-Tag": "-3", "SupplierSystem": "Test"},
            "body": json.dumps(self.mock_imms_payload),
            "pathParameters": {"id": self.mock_imms_id},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Validation errors: Immunization resource version:-3 in the request headers is invalid.",
        )

    def test_update_immunization_returns_error_for_invalid_id(self):
        """it should return a 400 error if the ID is invalid"""

        aws_event = {
            "headers": {"E-Tag": "1", "SupplierSystem": "Test"},
            "pathParameters": {"id": "invalid %$ id"},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")
        self.assertEqual(
            outcome["issue"][0]["diagnostics"],
            "Validation errors: the provided event ID is either missing or not in the expected format.",
        )
        self.service.update_immunization.assert_not_called()

    def test_update_immunization_returns_error_when_id_is_missing_from_path_params(self):
        """it should return a 400 error if pathParameters['id'] is missing"""
        aws_event = {
            "headers": {"E-Tag": "1", "SupplierSystem": "Test"},
            "body": '{"id": "valid-id"}',
            "pathParameters": {},  # 'id' is missing
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Validation errors: the provided event ID is either missing or not in the expected format.",
        )
        self.service.update_immunization.assert_not_called()

    def test_update_immunization_returns_error_when_invalid_json_provided(self):
        """it should return a 400 validation error if the body contains invalid JSON"""
        # Given
        aws_event = {
            "headers": {"E-Tag": "2", "SupplierSystem": "Test"},
            "body": '{"test": "broken}',
            "pathParameters": {"id": self.mock_imms_id},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Request's body contains malformed JSON: Unterminated string starting at: line 1 column 10 (char 9)",
        )
        self.service.update_immunization.assert_not_called()

    def test_update_immunization_returns_error_when_id_in_body_does_not_match_path(self):
        """it should return a 400 validation error if the Immunization resource body's ID does not match the path"""
        # Given
        aws_event = {
            "headers": {"E-Tag": "2", "SupplierSystem": "Test"},
            "body": json.dumps(self.mock_imms_payload),
            "pathParameters": {"id": "a-different-id"},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Validation errors: The provided immunization id:a-different-id doesn't match with the content of the request body",
        )
        self.service.update_immunization.assert_not_called()


class TestDeleteImmunization(unittest.TestCase):
    _MOCK_IMMS_ID = "1d8f5656-ef12-4d43-aaff-3cc54ae1970b"

    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.exception_wrapper_logger_patcher = patch("controller.fhir_api_exception_handler.logger")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.mock_exception_wrapper_logger = self.exception_wrapper_logger_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_validate_imms_id(self):
        """it should validate lambda's Immunization id"""
        invalid_id = {
            "pathParameters": {"id": "invalid %$ id"},
            "headers": {"SupplierSystem": "Test"},
        }

        response = self.controller.delete_immunization(invalid_id)

        self.assertEqual(self.service.get_immunization_and_version_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_unauthorised_delete_immunization(self):
        """it should return authorization error when the Supplier System header is not present"""
        aws_event = {"pathParameters": {"id": self._MOCK_IMMS_ID}, "headers": {}}
        response = self.controller.delete_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_delete_immunization(self):
        """it should mark the record as deleted successfully"""
        # Given
        self.service.delete_immunization.return_value = None
        lambda_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": self._MOCK_IMMS_ID},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.service.delete_immunization.assert_called_once_with(self._MOCK_IMMS_ID, "Test")

        self.assertEqual(response["statusCode"], 204)
        self.assertTrue("body" not in response)

    def test_delete_immunization_unauthorised_vax(self):
        # Given
        self.service.delete_immunization.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"SupplierSystem": "Test"},
            "pathParameters": {"id": self._MOCK_IMMS_ID},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 403)

    def test_immunization_exception_not_found(self):
        """it should return not-found OperationOutcome if service throws ResourceNotFoundError"""
        # Given
        error = ResourceNotFoundError(resource_type="Immunization", resource_id="an-error-id")
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"SupplierSystem": "Test"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertDictEqual(
            body,
            {
                "id": ANY,
                "issue": [
                    {
                        "code": "not-found",
                        "details": {
                            "coding": [
                                {"code": "NOT-FOUND", "system": "https://fhir.nhs.uk/Codesystem/http-error-codes"}
                            ]
                        },
                        "diagnostics": "Immunization resource does not exist. ID: an-error-id",
                        "severity": "error",
                    }
                ],
                "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
                "resourceType": "OperationOutcome",
            },
        )

    def test_immunization_unhandled_error(self):
        """it should return error OperationOutcome if an unhandled exception is thrown"""
        # Given
        error = Exception("Unhandled exception")
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"SupplierSystem": "Test"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertDictEqual(
            body,
            {
                "id": ANY,
                "issue": [
                    {
                        "code": "exception",
                        "details": {
                            "coding": [
                                {"code": "EXCEPTION", "system": "https://fhir.nhs.uk/Codesystem/http-error-codes"}
                            ]
                        },
                        "diagnostics": "Unable to process request. Issue may be transient.",
                        "severity": "error",
                    }
                ],
                "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
                "resourceType": "OperationOutcome",
            },
        )
        self.mock_exception_wrapper_logger.exception.assert_called_once_with("Unhandled exception")


class TestSearchImmunizations(TestFhirControllerBase):
    MOCK_REDIS_V2D_HKEYS = {
        "PERTUSSIS",
        "RSV",
        "3IN1",
        "MMR",
        "HPV",
        "MMRV",
        "PNEUMOCOCCAL",
        "SHINGLES",
        "COVID",
        "FLU",
        "MENACWY",
    }

    def setUp(self):
        super().setUp()
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.patient_identifier_key = "patient.identifier"
        self.immunization_target_key = "-immunization.target"
        self.date_from_key = "-date.from"
        self.date_to_key = "-date.to"
        self.nhs_number_valid_value = "9000000009"
        self.patient_identifier_valid_value = f"{patient_identifier_system}|{self.nhs_number_valid_value}"
        self.mock_redis.hkeys.return_value = self.MOCK_REDIS_V2D_HKEYS
        self.mock_redis_getter.return_value = self.mock_redis

    def test_get_search_immunizations(self):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result, False

        vaccine_type = "COVID"
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [
                (
                    f"{self.patient_identifier_key}",
                    f"{self.patient_identifier_valid_value}",
                )
            ]
        )
        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "test",
            },
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, "test", ANY, ANY
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_get_search_immunizations_vax_permission_check(self):
        """it should return a 403 error if the service raises an unauthorized error"""
        self.service.search_immunizations.side_effect = UnauthorizedVaxError()

        vaccine_type = "COVID"
        lambda_event = {
            "SupplierSystem": "test",
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search(
        self,
    ):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle, True

        vaccine_type = ["COVID", "FLU"]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "test",
            },
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        # Check if any resource in entry has resourceType "OperationOutcome"
        operation_outcome_present = any(
            entry["resource"]["resourceType"] == "OperationOutcome" for entry in body.get("entry", [])
        )
        self.assertTrue(
            operation_outcome_present,
            "OperationOutcome resource is not present in the response",
        )

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_400(self):
        """it should return 400 as the request has an invalid vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle, False

        vaccine_type = "FLUE"

        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "test",
            },
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_post_search_immunizations(self):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result, False

        vaccine_type = "COVID"
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [
                (
                    f"{self.patient_identifier_key}",
                    f"{self.patient_identifier_valid_value}",
                )
            ]
        )
        # Construct the application/x-www-form-urlencoded body
        body = {
            self.patient_identifier_key: self.patient_identifier_valid_value,
            self.immunization_target_key: vaccine_type,
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "Test",
            },
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, "Test", ANY, ANY
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_post_search_immunizations_for_unauthorized_vaccine_type_search(self):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle, True

        vaccine_type = "COVID", "FLU"
        vaccine_type = ",".join(vaccine_type)
        # Construct the application/x-www-form-urlencoded body
        body = {
            self.patient_identifier_key: self.patient_identifier_valid_value,
            self.immunization_target_key: vaccine_type,
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "Test",
            },
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        # Check if any resource in entry has resourceType "OperationOutcome"
        operation_outcome_present = any(
            entry["resource"]["resourceType"] == "OperationOutcome" for entry in body.get("entry", [])
        )
        self.assertTrue(
            operation_outcome_present,
            "OperationOutcome resource is not present in the response",
        )

    def test_post_search_immunizations_for_unauthorized_vaccine_type_search_400(self):
        """it should return 400 as the request is having invalid vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle, False

        vaccine_type = "FLUE"

        # Construct the application/x-www-form-urlencoded body
        body = {
            self.patient_identifier_key: self.patient_identifier_valid_value,
            self.immunization_target_key: vaccine_type,
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "flu:search",
            },
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_post_search_immunizations_for_unauthorized_vaccine_type_search_403(self):
        """it should return 403 as the user doesnt have vaccinetype permission"""
        self.service.search_immunizations.side_effect = UnauthorizedVaxError()

        vaccine_type = ["COVID", "FLU"]
        vaccine_type = ",".join(vaccine_type)

        # Construct the application/x-www-form-urlencoded body
        body = {
            self.patient_identifier_key: self.patient_identifier_valid_value,
            self.immunization_target_key: vaccine_type,
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "Test",
            },
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("controller.fhir_controller.process_search_params", wraps=process_search_params)
    def test_uses_parameter_parser(self, process_search_params: Mock):
        self.mock_redis.hkeys.return_value = self.MOCK_REDIS_V2D_HKEYS
        self.mock_redis_getter.return_value = self.mock_redis
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["a-disease-type"],
            }
        }

        self.controller.search_immunizations(lambda_event)

        process_search_params.assert_called_once_with(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["a-disease-type"],
            }
        )

    @patch("controller.fhir_controller.process_search_params")
    def test_search_immunizations_returns_400_on_ParameterException_from_parameter_parser(
        self, process_search_params: Mock
    ):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["a-disease-type"],
            }
        }

        process_search_params.side_effect = ParameterExceptionError("Test")
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_search_immunizations_returns_400_on_passing_superseded_nhs_number(self):
        """This method should return 400 as input parameter has superseded nhs number."""
        search_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.search_immunizations.return_value = search_result, False

        vaccine_type = "COVID"
        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "Test",
            },
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_search_immunizations_returns_200_remove_vaccine_not_done(self):
        """This method should return 200 but remove the data which has status as not done."""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle, False
        vaccine_type = "COVID"
        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "Test",
            },
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        for entry in body.get("entry", []):
            self.assertNotEqual(entry.get("resource", {}).get("status"), "not-done", "entered-in-error")

    def test_self_link_excludes_extraneous_params(self):
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result, False
        vaccine_type = "COVID"
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [
                (
                    f"{self.patient_identifier_key}",
                    f"{self.patient_identifier_valid_value}",
                )
            ]
        )

        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.immunization_target_key: [vaccine_type],
                "b": ["b,a"],
                "a": ["b,a"],
            },
            "body": None,
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "SupplierSystem": "Test",
            },
            "httpMethod": "POST",
        }

        self.controller.search_immunizations(lambda_event)

        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, "Test", ANY, ANY
        )
