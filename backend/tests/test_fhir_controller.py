import base64
import urllib

import json
import unittest
import uuid

from unittest.mock import patch
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.immunization import Immunization
from unittest.mock import create_autospec, ANY, patch, Mock
from urllib.parse import urlencode
import urllib.parse
from moto import mock_aws
from authorization import Authorization
from fhir_controller import FhirController
from fhir_repository import ImmunizationRepository
from fhir_service import FhirService, UpdateOutcome
from models.errors import (
    ResourceNotFoundError,
    UnhandledResponseError,
    InvalidPatientId,
    CustomValidationError,
    ParameterException,
    InconsistentIdError,
    UnauthorizedVaxError,
    UnauthorizedError,
    IdentifierDuplicationError,
)
from tests.utils.immunization_utils import create_covid_19_immunization
from mappings import VaccineTypes
from parameter_parser import patient_identifier_system, process_search_params
from tests.utils.generic_utils import load_json_data
from tests.utils.values_for_tests import ValidValues

"test"


class TestFhirController(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.repository = create_autospec(ImmunizationRepository)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    def test_create_response(self):
        """it should return application/fhir+json with correct status code"""
        body = {"message": "a body"}
        res = self.controller.create_response(42, body)
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
        res = self.controller.create_response(42)
        self.assertEqual(res["statusCode"], 42)
        self.assertDictEqual(res["headers"], {})
        self.assertTrue("body" not in res)


class TestFhirControllerGetImmunizationByIdentifier(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer(self, mock_get_permissions):
        """it should return Immunization Id if it exists"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": None,
        }
        identifier = lambda_event.get("queryStringParameters", {}).get("immunization.identifier")
        _element = lambda_event.get("queryStringParameters", {}).get("_element")

        identifiers = identifier.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, ["COVID19.CUDS"], identifier, _element
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_no_vax_permission(self, mock_get_permissions):
        """it should return Immunization Id if it exists"""
        # Given
        mock_get_permissions.return_value = []
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.assertEqual(response["statusCode"], 403)

    def test_get_imms_by_identifer_header_missing(self):
        """it should return Immunization Id if it exists"""
        # Given
        lambda_event = {
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(response["statusCode"], 403)
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_not_found_for_identifier(self, mock_get_permissions):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        mock_get_permissions.return_value = ["COVID19.S"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/Immunization?immunization.target=COVID19&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7C1345678940",
                }
            ],
            "entry": [],
            "total": 0,
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
                "SupplierSystem": "test",
            },
            "body": None,
        }
        identifier = lambda_event.get("queryStringParameters", {}).get("immunization.identifier")
        _element = lambda_event.get("queryStringParameters", {}).get("_element")

        imms = identifier.replace("|", "#")
        # When
        
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_identifier.assert_called_once_with(
            imms, ["COVID19.S"], identifier, _element
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        self.assertEqual(body["entry"], [])
        self.assertEqual(body["total"], 0)

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_patient_identifier_and_element_present(self, mock_get_supplier_permissions):
        """it should return Immunization Id if it exists"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]

        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {"patient.identifier": "test", "_element": "id,meta"},
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_both_body_and_query_params_present(self, mock_get_supplier_permissions):
        """it should return Immunization Id if it exists"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "patient.identifier": "test",
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD1pZCUyQ21ldGEmaWQ9cw==",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_imms_identifier_and_element_not_present(self, mock_get_supplier_permissions):
        """it should return Immunization Id if it exists"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "-immunization.target": "test",
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_both_identifier_present(self, mock_get_supplier_permissions):
        """it should return Immunization Id if it exists"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": {
                "patient.identifier": "test",
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_invalid_element(self, mock_get_supplier_permissions):
        """it should return 400 as it contain invalid _element if it exists"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta,name",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_identifier_is_empty(self, mock_get_supplier_permissions):
        """it should return 400 as identifierSystem is missing"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {"immunization.identifier": "", "_element": "id"},
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_element_is_empty(self, mock_get_supplier_permissions):
        """it should return 400 as element is missing"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": {"immunization.identifier": "test|123", "_element": ""},
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_identifier_in_invalid_format(self,mock_get_supplier_permissions):
        """it should return 400 as identifierSystem is missing"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "immunization.identifier must be in the format of immunization.identifier.system|immunization.identifier.value e.g. http://pinnacle.org/vaccs|2345-gh3s-r53h7-12ny",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vaccf10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id",
            },
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_identifier_having_whitespace(self,mock_get_supplier_permissions):
        """it should return 400 as identifierSystem is missing"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc  |   f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id",
            },
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_imms_id_invalid_vaccinetype(self, mock_get_permissions):
        """it should validate lambda's Immunization id"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id",
            },
            "body": None,
        }
        identifier = lambda_event.get("queryStringParameters", {}).get("immunization.identifier")
        _element = lambda_event.get("queryStringParameters", {}).get("_element")
        identifiers = identifier.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, ["COVID19.CRUDS"], identifier, _element
        )

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")


class TestFhirControllerGetImmunizationByIdentifierPost(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    def set_up_lambda_event(self, body):
        """Helper to create and set up a lambda event with the given body"""
        return {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD1pZCUyQ21ldGEmaWQ9cw==",
        }

    def parse_lambda_body(self, lambda_event):
        """Helper to parse and decode lambda event body"""
        decoded_body = base64.b64decode(lambda_event["body"]).decode("utf-8")
        parsed_body = urllib.parse.parse_qs(decoded_body)
        immunization_identifier = parsed_body.get("immunization.identifier", "")
        converted_identifier = "".join(immunization_identifier)
        element = parsed_body.get("_element", "")
        converted_element = "".join(element)
        identifiers = converted_identifier.replace("|", "#")
        return identifiers, converted_identifier, converted_element

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifier(self,mock_get_permissions):
        """It should return Immunization Id if it exists"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        body = "immunization.identifier=https://supplierABC/identifiers/vacc#f10b59b3-fc73-4616-99c9-9e882ab31184&_element=id|meta"
        lambda_event = self.set_up_lambda_event(body)
        identifiers, converted_identifier, converted_element = self.parse_lambda_body(lambda_event)

        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, ["COVID19.CRUDS"], converted_identifier, converted_element
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    @patch("fhir_controller.get_supplier_permissions")
    def test_not_found_for_identifier(self, mock_get_permissions):
        """It should return not-found OperationOutcome if it doesn't exist"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/Immunization?immunization.target=COVID19&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7C1345678940",
                }
            ],
            "entry": [],
            "total": 0,
        }
        body = "immunization.identifier=https://supplierABC/identifiers/vacc#f10b59b3-fc73-4616-99c9-9e882ab31184&_element=id|meta"
        lambda_event = self.set_up_lambda_event(body)
        identifiers, converted_identifier, converted_element = self.parse_lambda_body(lambda_event)

        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, ["COVID19.CRUDS"], converted_identifier, converted_element
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        self.assertEqual(body["entry"], [])
        self.assertEqual(body["total"], 0)

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_patient_identifier_and_element_present(self, mock_get_permissions):
        """it should return 400 as its having invalid request"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "cGF0aWVudC5pZGVudGlmaWVyPWh0dHBzJTNBJTJGJTJGZmhpci5uaHMudWslMkZJZCUyRm5ocy1udW1iZXIlN0M5NjkzNjMyMTA5Jl9lbGVtZW50PWlkJTJDbWV0YQ==",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_imms_identifier_and_element_not_present(self,mock_get_supplier_permissons):
        """it should return 400 as its having invalid request"""
        mock_get_supplier_permissons.return_value = ["COVID19.CRUDS"]
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "LWltbXVuaXphdGlvbi50YXJnZXQ9Q09WSUQxOSZpbW11bml6YXRpb24uaWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJTdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_element_is_empty(self,mock_get_supplier_permissions):
        """it should return 400 as element is missing"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": { "SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD0nJw==",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_identifier_is_invalid(self,mock_get_supplier_permissions):
        """it should return 400 as identifierSystem is invalid"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
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

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_both_identifier_present(self, mock_get_supplier_permissions):
        """it should return 400 as its having invalid request"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "cGF0aWVudC5pZGVudGlmaWVyPWh0dHBzJTNBJTJGJTJGZmhpci5uaHMudWslMkZJZCUyRm5ocy1udW1iZXIlN0M5NjkzNjMyMTA5Ji1pbW11bml6YXRpb24udGFyZ2V0PUNPVklEMTkmX2luY2x1ZGU9SW1tdW5pemF0aW9uJTNBcGF0aWVudCZpbW11bml6YXRpb24uaWRlbnRpZmllcj1odHRwcyUzQSUyRiUyRnN1cHBsaWVyQUJDJTJGaWRlbnRpZmllcnMlMkZ2YWNjJTdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50PWlkJTJDbWV0YSZpZD1z",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_not_called

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_identifer_invalid_element(self, mock_get_supplier_permissions):
        """it should return 400 as it contain invalid _element if it exists"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD1pZCUyQ21ldGElMkNuYW1l",
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_identifier_is_empty(self, mock_get_supplier_permissions):
        """it should return 400 as identifierSystem is missing"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.return_value = {
            "resourceType": "OperationOutcome",
            "id": "f6857e0e-40d0-4e5e-9e2f-463f87d357c6",
            "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "immunization.identifier must be in the format of immunization.identifier.system|immunization.identifier.value e.g. http://pinnacle.org/vaccs|2345-gh3s-r53h7-12ny",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9Jl9lbGVtZW50PWlkJTJDbWV0YQ==",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_immunization_identifier_having_whitespace(self,mock_get_supplier_permissions):
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyUgIDdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50PWlkJTJDbWV0YSZpZD1z",
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")
   
    @patch("fhir_controller.get_supplier_permissions")
    def test_validate_imms_id_invalid_vaccinetype(self, mock_get_permissions):
        """it should validate lambda's Immunization id"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        self.service.get_immunization_by_identifier.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD1pZCUyQ21ldGEmaWQ9cw==",
        }
        decoded_body = base64.b64decode(lambda_event["body"]).decode("utf-8")
        # Parse the URL encoded body
        parsed_body = urllib.parse.parse_qs(decoded_body)

        immunization_identifier = parsed_body.get("immunization.identifier", "")
        converted_identifer = "".join(immunization_identifier)
        element = parsed_body.get("_element", "")
        converted_element = "".join(element)

        identifiers = converted_identifer.replace("|", "#")
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        mock_get_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, ["COVID19.CRUDS"], converted_identifer, converted_element
        )

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "forbidden")


class TestFhirControllerGetImmunizationById(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_id(self, mock_permissions):
        """it should return Immunization resource if it exists"""
        # Given
        mock_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = "a-id"
        self.service.get_immunization_by_id.return_value = Immunization.construct()
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        mock_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, ["COVID19.CRUDS"])

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Immunization")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_id_unauthorised_vax_error(self,mock_permissions):
        """it should return Immunization resource if it exists"""
        # Given
        mock_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = "a-id"
        self.service.get_immunization_by_id.side_effect = UnauthorizedVaxError
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        mock_permissions.assert_called_once_with("test")
        self.assertEqual(response["statusCode"], 403)
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_get_imms_by_id_no_vax_permission(self, mock_permissions):
        """it should return Immunization Id if it exists"""
        # Given
        mock_permissions.return_value = []
        imms_id = "a-id"
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        mock_permissions.assert_called_once_with("test")
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_not_found(self,mock_permissions):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        mock_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)

        # Then
        mock_permissions.assert_called_once_with("test")
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, ["COVID19.CRUDS"])

        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    def test_validate_imms_id(self):
        """it should validate lambda's Immunization id"""
        invalid_id = {"pathParameters": {"id": "invalid %$ id"}}

        response = self.controller.get_immunization_by_id(invalid_id)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")


class TestCreateImmunization(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    @patch("fhir_controller.get_supplier_permissions")
    def test_create_immunization(self,mock_get_permissions):
        """it should create Immunization and return resource's location"""
        mock_get_permissions.return_value = ["COVID19.CRUDS", "FLU.CRUDS"]
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        self.service.create_immunization.return_value = imms

        response = self.controller.create_immunization(aws_event)

        imms_obj = json.loads(aws_event["body"])
        mock_get_permissions.assert_called_once_with("Test")
        self.service.create_immunization.assert_called_once_with(imms_obj, ["COVID19.CRUDS", "FLU.CRUDS"], "Test")
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{imms_id}"))

    @patch("fhir_controller.get_supplier_permissions")
    def test_create_immunization_UnauthorizedVaxError_check_for_non_batch(self, mock_get_permissions):
        """it should not create the Immunization record"""
        mock_get_permissions.return_value = []
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        response = self.controller.create_immunization(aws_event)
        mock_get_permissions.assert_called_once_with("Test")
        self.assertEqual(response["statusCode"], 403)

    def test_unauthorised_create_immunization(self):
        """it should return authorization error"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {"body": imms.json()}
        response = self.controller.create_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_create_immunization_for_unauthorized(self, mock_permissions):
        """It should create Immunization and return resource's location"""
        # Given
        mock_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
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
        mock_permissions.assert_called_once_with("test")
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_malformed_resource(self, mock_permissions):
        """it should return 400 if json is malformed"""
        mock_permissions.return_value = ["COVID19.CRUDS"]
        bad_json = '{foo: "bar"}'
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": bad_json,
        }

        response = self.controller.create_immunization(aws_event)
        mock_permissions.assert_called_once_with("Test")
        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_create_bad_request_for_superseded_number_for_create_immunization(self,mock_get_permissions):
        """it should return 400 if json has superseded nhs number."""
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        # Given
        create_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.create_immunization.return_value = create_result
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        # When
        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        mock_get_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_invalid_nhs_number(self,mock_get_permissions):
        """it should handle ValidationError when patient doesn't exist"""
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        # Given
        imms = Immunization.construct()
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        invalid_nhs_num = "a-bad-id"
        self.service.create_immunization.side_effect = InvalidPatientId(patient_identifier=invalid_nhs_num)

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        mock_get_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue(invalid_nhs_num in body["issue"][0]["diagnostics"])

    @patch("fhir_controller.get_supplier_permissions")
    def test_pds_unhandled_error(self,mock_get_permissions):
        """it should respond with 500 if PDS returns error"""
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        imms = Immunization.construct()
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms.json(),
        }
        self.service.create_immunization.side_effect = UnhandledResponseError(response={}, message="a message")

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(500, response["statusCode"])
        mock_get_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")


class TestUpdateImmunization(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization(self,mock_get_permissions):
        """it should update Immunization"""
        mock_get_permissions.return_value = ["COVID19.CRUD"]
        # Given
        imms_id = "valid-id"
        imms = '{"id": "valid-id"}'
        aws_event = {
            "headers": {"E-Tag": 1,"SupplierSystem": "Test"},
            "body": imms,
            "pathParameters": {"id": imms_id},
        }
        self.service.update_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)

        self.service.update_immunization.assert_called_once_with(
            imms_id, json.loads(imms), 1, ["COVID19.CRUD"], "Test"
        )
        mock_get_permissions.assert_called_once_with("Test")
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_etag_missing(self, mock_get_supplier_permissions):
        """it should update Immunization"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUD"]
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        self.service.get_immunization_by_id_all.return_value = {
        "id": imms_id,
        "Version": 1,
        "VaccineType": "COVID19",
        "DeletedAt": False
    }
        aws_event = {
            "headers": {
                "SupplierSystem": "Test",
                "operation_requested": "update"
            },
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn(
            "Validation errors: Immunization resource version not specified in the request headers",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_duplicate(self, mock_get_supplier_permissions):
        """it should not update the Immunization record"""
        mock_get_supplier_permissions.return_value = ["COVID19.U"]
        # Given
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "SupplierSystem": "Test",
                "operation_requested": "update"
            },
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }
        self.service.update_immunization.side_effect = IdentifierDuplicationError(identifier="test")
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 422)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_UnauthorizedVaxError(self, mock_get_supplier_permissions):
        """it should not update the Immunization record"""
        mock_get_supplier_permissions.return_value = ["COVID19.U"]
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "SupplierSystem": "Test",
                "operation_requested": "update"
            },
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }
        self.service.update_immunization.side_effect = UnauthorizedVaxError()
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)
        mock_get_supplier_permissions.assert_called_once_with("Test")
        self.assertEqual(response["statusCode"], 403)
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_UnauthorizedVaxError_check_for_non_batch(self, mock_get_supplier_permissions):
        """it should not update the Immunization record"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRDS"]
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }
        response = self.controller.update_immunization(aws_event)
        mock_get_supplier_permissions.assert_called_once_with("Test")
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_Unauthorizedsystem_check_for_non_batch(self, mock_get_supplier_permissions):
        """it should not update the Immunization record"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRD"]
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }

        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_for_batch_existing_record_is_none(self, mock_get_supplier_permissions):
        """it should update Immunization"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "SupplierSystem": "Test",
                "operation_requested": "update"
            },
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }
        self.service.update_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"
        self.service.get_immunization_by_id_all.return_value = None
        response = self.controller.update_immunization(aws_event)

        # self.service.update_immunization.assert_called_once_with(imms_id, json.loads(imms), 1, "COVID19.CRUDS", "Test", False)
        self.assertEqual(response["statusCode"], 404)
        mock_get_supplier_permissions.assert_called_once_with("Test")
        self.assertIn(
            "The requested immunization resource with id:valid-id was not found.",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    def test_unauthorised_update_immunization(self):
        """it should return authorization error"""
        aws_event = {"body": ()}
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_for_invalid_version(self, mock_get_supplier_permissions):
        """it should not update Immunization"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        # Given
        imms = '{"id": "valid-id"}'
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": "ajjsajj", "SupplierSystem": "Test"},
            "body": json.dumps(imms),
            "pathParameters": {"id": imms_id},
        }
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        mock_get_supplier_permissions.assert_called_once_with("Test")

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_deletedat_immunization_with_version(self, mock_get_supplier_permissions):
        """it should reinstate deletedat Immunization"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        imms = '{"id": "valid-id"}'
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": imms,
            "pathParameters": {"id": imms_id},
        }
        self.service.reinstate_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": True,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)

        self.service.reinstate_immunization.assert_called_once_with(
            imms_id, json.loads(imms), 1, ["COVID19.CRUDS"], "Test"
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_deletedat_immunization_without_version(self, mock_get_supplier_permissions):
        """it should reinstate deletedat Immunization"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUD"]
        # Given
        imms = '{"id": "valid-id"}'
        imms_id = "valid-id"
        aws_event = {
            "headers": {"SupplierSystem": "Test"},
            "body": imms,
            "pathParameters": {"id": imms_id},
        }
        self.service.reinstate_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": True,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)

        self.service.reinstate_immunization.assert_called_once_with(
            imms_id, json.loads(imms), 1, ["COVID19.CRUD"], "Test"
        )
        mock_get_supplier_permissions.assert_called_once_with("Test")
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_record_exists(self, mock_get_supplier_permissions):
        """it should return not-found OperationOutcome if ID doesn't exist"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)

        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, ["COVID19.CRUDS"])

        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validation_error(self, mock_get_supplier_permissions):
        """it should return 400 if Immunization is invalid"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUD"]
        # Given
        imms = '{"id": "valid-id"}'
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": imms,
            "pathParameters": {"id": "valid-id"},
        }
        self.service.update_immunization.side_effect = CustomValidationError(message="invalid")
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(400, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")


    @patch("fhir_controller.get_supplier_permissions")
    def test_validation_error_for_batch(self, mock_get_supplier_permissions):
        """it should return 400 if Immunization is invalid"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        imms = '{"id": 123}'
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "SupplierSystem": "Test",
                "operation_requested": "update"
            },
            "body": imms,
            "pathParameters": {"id": "valid-id"},
        }
        self.service.update_immunization.side_effect = CustomValidationError(message="invalid")
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(400, response["statusCode"])
        mock_get_supplier_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validation_superseded_number_to_give_bad_request_for_update_immunization(self, mock_get_supplier_permissions):
        """it should return 400 if Immunization has superseded nhs number."""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUD"]
        update_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.update_immunization.return_value = None, update_result
        req_imms = '{"id": "valid-id"}'
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": req_imms,
            "pathParameters": {"id": path_id},
        }
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 1,
            "DeletedAt": False,
            "Reinstated": False,
            "VaccineType": "COVID19",
        }
        # When
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_validation_identifier_to_give_bad_request_for_update_immunization(self, mock_get_supplier_permissions):
        """it should return 400 if Identifier system and value  doesn't match with the stored content."""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        req_imms = '{"id": "valid-id"}'
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19.CRUDS", "SupplierSystem": "Test"},
            "body": req_imms,
            "pathParameters": {"id": path_id},
        }
        self.service.get_immunization_by_id_all.return_value = {
            "diagnostics": "Validation errors: identifier[0].system doesn't match with the stored content"
        }
        # When
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_version_mismatch_for_update_immunization(self, mock_get_supplier_permissions):
        """it should return 400 if resource version mismatch"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUD"]
        update_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.update_immunization.return_value = None, update_result
        req_imms = '{"id": "valid-id"}'
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": req_imms,
            "pathParameters": {"id": path_id},
        }
        self.service.get_immunization_by_id_all.return_value = {
            "resource": "new_value",
            "Version": 2,
            "DeletedAt": False,
            "VaccineType": "COVID19",
        }
        # When
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_for_batch(self, mock_get_supplier_permissions):
        """Immunization[id] should exist and be the same as request"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        bad_json = "{}"
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "body": bad_json,
            "pathParameters": {"id": "an-id"},
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn(
            "The provided immunization id:an-id doesn't match with the content of the request body",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    @patch("fhir_controller.get_supplier_permissions")
    def test_update_immunization_for_batch_with_invalid_json(self, mock_get_supplier_permissions):
        """it should validate lambda's Immunization id"""
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": "invalid %$ id"},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(self.service.update_immunization.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")


class TestDeleteImmunization(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    def test_validate_imms_id(self):
        """it should validate lambda's Immunization id"""
        invalid_id = {"pathParameters": {"id": "invalid %$ id"}, "headers": {"SupplierSystem": "Test"}}

        response = self.controller.delete_immunization(invalid_id)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_delete_immunization_UnauthorizedVaxError_check_for_non_batch(self, mock_get_supplier_permissions):
        """it should not delete the Immunization record"""
        mock_get_supplier_permissions.return_value = []
        imms_id = "an-id"
        aws_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": imms_id},
        }
        response = self.controller.delete_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_unauthorised_delete_immunization(self):
        """it should return authorization error"""
        aws_event = {"body": ()}
        response = self.controller.delete_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_delete_immunization(self, mock_get_supplier_permissions):
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        imms_id = "an-id"
        self.service.delete_immunization.return_value = Immunization.construct()
        lambda_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.service.delete_immunization.assert_called_once_with(imms_id, ["COVID19.CRUDS"], "Test")

        self.assertEqual(response["statusCode"], 204)
        self.assertTrue("body" not in response)

    @patch("fhir_controller.sqs_client.send_message")
    @patch("fhir_controller.get_supplier_permissions")
    def test_delete_immunization_unauthorised_vax(self, mock_sqs_message,mock_get_permissions):
        # Given
        imms_id = "an-id"
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        self.service.delete_immunization.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {
                "SupplierSystem": "Test",
                "operation_requested": "delete"
            },
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_immunization_exception_not_found(self, mock_get_permissions):
        """it should return not-found OperationOutcome if service throws ResourceNotFoundError"""
        # Given
        mock_get_permissions.return_value = ["COVID19.CRUDS"]
        error = ResourceNotFoundError(resource_type="Immunization", resource_id="an-error-id")
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 404)
        mock_get_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")
    
    @patch("fhir_controller.get_supplier_permissions")
    def test_immunization_unhandled_error(self, mock_get_supplier_permissions):
        """it should return server-error OperationOutcome if service throws UnhandledResponseError"""
        # Given
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        error = UnhandledResponseError(message="a message", response={})
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"E-Tag": 1, "SupplierSystem": "Test"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 500)
        mock_get_supplier_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")

class TestSearchImmunizations(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)
        self.patient_identifier_key = "patient.identifier"
        self.immunization_target_key = "-immunization.target"
        self.date_from_key = "-date.from"
        self.date_to_key = "-date.to"
        self.nhs_number_valid_value = "9000000009"
        self.patient_identifier_valid_value = f"{patient_identifier_system}|{self.nhs_number_valid_value}"

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_search_immunizations(self, mock_get_supplier_permissions):
        """it should search based on patient_identifier and immunization_target"""
        
        mock_get_supplier_permissions.return_value = ["COVID19.S"]
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = "COVID19"
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [(f"{self.patient_identifier_key}", f"{self.patient_identifier_valid_value}")]
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
        mock_get_supplier_permissions.assert_called_once_with("test")
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_search_immunizations_vax_permission_check(self, mock_get_supplier_permissions):
        """it should search based on patient_identifier and immunization_target"""
        mock_get_supplier_permissions.return_value = []
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
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

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_search_immunizations_for_unauthorized_vaccine_type_search(self, mock_get_supplier_permissions):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        mock_get_supplier_permissions.return_value = ["covid19.S"]
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "test",},
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
        self.assertTrue(operation_outcome_present, "OperationOutcome resource is not present in the response")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_400(self,mock_get_supplier_permissions):
        """it should return 400 as the the request is having invalid vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        mock_get_supplier_permissions.return_value = ["covid19.S"]
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = "FLUE"

        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "test"},
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

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_403(self, mock_get_supplier_permissions):
        """it should return 403 as the user doesnt have vaccinetype permission"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        mock_get_supplier_permissions.return_value = []
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "test",},
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        mock_get_supplier_permissions.assert_called_once_with("test")
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_get_search_immunizations_unauthorized(self, mock_get_supplier_permissions):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        mock_get_supplier_permissions.return_value = []
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [(f"{self.patient_identifier_key}", f"{self.patient_identifier_valid_value}")]
        )
        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        mock_get_supplier_permissions.assert_called_once_with("test")
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.get_supplier_permissions")
    def test_post_search_immunizations(self,mock_get_supplier_permissions):
        """it should search based on patient_identifier and immunization_target"""
        mock_get_supplier_permissions.return_value = ["covid19.s"]
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = "COVID19"
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [(f"{self.patient_identifier_key}", f"{self.patient_identifier_valid_value}")]
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
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "Test"},
            "body": base64_encoded_body,
        }
        
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
        self.assertEqual(response["statusCode"], 200)
        mock_get_supplier_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    @patch("fhir_controller.get_supplier_permissions")
    def test_post_search_immunizations_for_unauthorized_vaccine_type_search(self,mock_get_supplier_permissions):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle
        mock_get_supplier_permissions.return_value = ["covid19.s"]

        vaccine_type = "COVID19", "FLU"
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
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "Test"},
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
        self.assertTrue(operation_outcome_present, "OperationOutcome resource is not present in the response")

    def test_post_search_immunizations_for_unauthorized_vaccine_type_search_400(self):
        """it should return 400 as the the request is having invalid vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

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
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": "flu:search"},
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_post_search_immunizations_for_unauthorized_vaccine_type_search_403(self, mock_get_supplier_permissions):
        """it should return 403 as the user doesnt have vaccinetype permission"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        mock_get_supplier_permissions.return_value = []
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
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
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "Test"},
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.process_search_params", wraps=process_search_params)
    def test_uses_parameter_parser(self, process_search_params: Mock):
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

    @patch("fhir_controller.process_search_params")
    def test_search_immunizations_returns_400_on_ParameterException_from_parameter_parser(
        self, process_search_params: Mock
    ):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["a-disease-type"],
            }
        }

        process_search_params.side_effect = ParameterException("Test")
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_search_immunizations_returns_400_on_passing_superseded_nhs_number(self, mock_get_supplier_permissions):
        "This method should return 400 as input paramter has superseded nhs number."
        search_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.search_immunizations.return_value = search_result
        mock_get_supplier_permissions.return_value = ["covid19.s"]

        vaccine_type = "COVID19"
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
        mock_get_supplier_permissions.assert_called_once_with("Test")
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @patch("fhir_controller.get_supplier_permissions")
    def test_search_immunizations_returns_200_remove_vaccine_not_done(self, mock_get_supplier_permissions):
        "This method should return 200 but remove the data which has status as not done."
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        mock_get_supplier_permissions.return_value = ["COVID19.CRUDS"]
        self.service.search_immunizations.return_value = bundle
        vaccine_type = "COVID19"
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

    @patch("fhir_controller.get_supplier_permissions")
    def test_self_link_excludes_extraneous_params(self, mock_get_supplier_permissions):
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result
        vaccine_type = VaccineTypes().all[0]
        mock_get_supplier_permissions.return_value = ["covid19.CUDS"]
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [(f"{self.patient_identifier_key}", f"{self.patient_identifier_valid_value}")]
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
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
