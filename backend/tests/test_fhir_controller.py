import base64
import urllib

import json
import unittest
import uuid

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

    def test_get_imms_by_identifer(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "COVID19:search", identifier, _element, False
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    def test_get_imms_by_identifer_no_vax_permission(self):
        """it should return Immunization Id if it exists"""
        # Given
        lambda_event = {
            "headers": {"VaccineTypePermissions": "", "SupplierSystem": "test"},
            "queryStringParameters": {
                "immunization.identifier": "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184",
                "_element": "id,meta",
            },
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)
        # Then
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

    def test_get_imms_by_identifer_for_batch(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "Imms-Batch-App"},
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, None, identifier, _element, True
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    def test_not_found_for_identifier(self):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
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
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            imms, "COVID19:search", identifier, _element, False
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        self.assertEqual(body["entry"], [])
        self.assertEqual(body["total"], 0)

    def test_get_imms_by_identifer_patient_identifier_and_element_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifer_both_body_and_query_params_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifer_imms_identifier_and_element_not_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifer_both_identifier_present(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifer_invalid_element(self):
        """it should return 400 as it contain invalid _element if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
            "queryStringParameters": {"immunization.identifier": "", "_element": "id"},
            "body": None,
        }
        response = self.controller.get_immunization_by_identifier(lambda_event)

        self.assertEqual(self.service.get_immunization_by_identifier.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
            "queryStringParameters": {"immunization.identifier": "test|123", "_element": ""},
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "immunization.identifier must be in the format of immunization.identifier.system|immunization.identifier.value e.g. http://pinnacle.org/vaccs|2345-gh3s-r53h7-12ny",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_validate_imms_id_invalid_vaccinetype(self):
        """it should validate lambda's Immunization id"""
        # Given
        self.service.get_immunization_by_identifier.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "COVID19:search", identifier, _element, False
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
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifier(self):
        """It should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        body = "immunization.identifier=https://supplierABC/identifiers/vacc#f10b59b3-fc73-4616-99c9-9e882ab31184&_element=id|meta"
        lambda_event = self.set_up_lambda_event(body)
        identifiers, converted_identifier, converted_element = self.parse_lambda_body(lambda_event)

        # When
        response = self.controller.get_immunization_by_identifier(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "COVID19:search", converted_identifier, converted_element, False
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "COVID19:search", converted_identifier, converted_element, False
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")
        self.assertEqual(body["entry"], [])
        self.assertEqual(body["total"], 0)

    def test_get_imms_by_identifer_for_batch(self):
        """it should return Immunization Id if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "Imms-Batch-App"},
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, None, converted_identifer, converted_element, True
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["id"], "test")

    def test_get_imms_by_identifer_patient_identifier_and_element_present(self):
        """it should return 400 as its having invalid request"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifer_imms_identifier_and_element_not_present(self):
        """it should return 400 as its having invalid request"""
        # Given
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
        self.service.get_immunization_by_identifier.return_value = {"id": "test", "Version": 1}
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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

    def test_get_imms_by_identifer_invalid_element(self):
        """it should return 400 as it contain invalid _element if it exists"""
        # Given
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyU3Q2YxMGI1OWIzLWZjNzMtNDYxNi05OWM5LTllODgyYWIzMTE4NCZfZWxlbWVudD1pZCUyQ21ldGElMkNuYW1l",
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "immunization.identifier must be in the format of immunization.identifier.system|immunization.identifier.value e.g. http://pinnacle.org/vaccs|2345-gh3s-r53h7-12ny",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9Jl9lbGVtZW50PWlkJTJDbWV0YQ==",
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
                        "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "INVALID"}]
                    },
                    "diagnostics": "The provided identifiervalue is either missing or not in the expected format.",
                }
            ],
        }
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
            "queryStringParameters": None,
            "body": "aW1tdW5pemF0aW9uLmlkZW50aWZpZXI9aHR0cHMlM0ElMkYlMkZzdXBwbGllckFCQyUyRmlkZW50aWZpZXJzJTJGdmFjYyUgIDdDZjEwYjU5YjMtZmM3My00NjE2LTk5YzktOWU4ODJhYjMxMTg0Jl9lbGVtZW50PWlkJTJDbWV0YSZpZD1z",
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
            "headers": {"VaccineTypePermissions": "COVID19:search", "SupplierSystem": "test"},
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
        self.service.get_immunization_by_identifier.assert_called_once_with(
            identifiers, "COVID19:search", converted_identifer, converted_element, False
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

    def test_get_imms_by_id(self):
        """it should return Immunization resource if it exists"""
        # Given
        imms_id = "a-id"
        self.service.get_immunization_by_id.return_value = Immunization.construct()
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:read"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, "COVID19:read")

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Immunization")

    def test_get_imms_by_id_unauthorised_vax_error(self):
        """it should return Immunization resource if it exists"""
        # Given
        imms_id = "a-id"
        self.service.get_immunization_by_id.side_effect = UnauthorizedVaxError
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:read"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.assertEqual(response["statusCode"], 403)

    def test_get_imms_by_id_no_vax_permission(self):
        """it should return Immunization Id if it exists"""
        # Given
        imms_id = "a-id"
        lambda_event = {
            "headers": {"VaccineTypePermissions": "", "SupplierSystem": "test"},
            "pathParameters": {"id": imms_id},
            "body": None,
        }
        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.assertEqual(response["statusCode"], 403)

    def test_not_found(self):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:read"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)

        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, "COVID19:read")

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

    def test_create_immunization(self):
        """it should create Immunization and return resource's location"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": imms.json(),
        }
        self.service.create_immunization.return_value = imms

        response = self.controller.create_immunization(aws_event)

        imms_obj = json.loads(aws_event["body"])
        self.service.create_immunization.assert_called_once_with(imms_obj, "COVID19:create", "Test", False)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{imms_id}"))

    def test_create_immunization_UnauthorizedVaxError_check_for_non_batch(self):
        """it should not create the Immunization record"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {"VaccineTypePermissions": "", "SupplierSystem": "Test"},
            "body": imms.json(),
        }
        response = self.controller.create_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_unauthorised_create_immunization(self):
        """it should return authorization error"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {"body": imms.json()}
        response = self.controller.create_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @mock_aws
    @patch("fhir_controller.sqs_client.send_message")
    def test_create_immunization_for_batch(self, mock_send_message):
        """It should create Immunization and return resource's location"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:create",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "create"
            },
            "body": imms.json(),
        }
        # Mock the create_immunization return value
        self.service.create_immunization.return_value = imms

        # Execute the function under test
        response = self.controller.create_immunization(aws_event)

        # Verify the SQS send_message was called
        expected_message_body = json.dumps(
            {
                "statusCode": 201,
                "headers": {"Location": f"https://internal-dev.api.service.nhs.uk/None/Immunization/{imms_id}"},
                "file_key": aws_event["headers"]["file_key"],
                "row_id": aws_event["headers"]["row_id"],
                "created_at_formatted_string": aws_event["headers"]["created_at_formatted_string"],
                "local_id": aws_event["headers"]["local_id"],
                "operation_requested": "create"
            }
        )

        mock_send_message.assert_called_once_with(
            QueueUrl="Queue_url", MessageBody=expected_message_body, MessageGroupId=aws_event["headers"]["file_key"]
        )

        # Assert the response
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{imms_id}"))

    def test_create_immunization_for_unauthorized(self):
        """It should create Immunization and return resource's location"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:create",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "create"
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
            "headers": {"VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": bad_json,
        }

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_create_bad_request_for_superseded_number_for_create_immunization(self):
        """it should return 400 if json has superseded nhs number."""
        create_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.create_immunization.return_value = create_result
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": imms.json(),
        }
        # When
        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_invalid_nhs_number(self):
        """it should handle ValidationError when patient doesn't exist"""
        imms = Immunization.construct()
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": imms.json(),
        }
        invalid_nhs_num = "a-bad-id"
        self.service.create_immunization.side_effect = InvalidPatientId(patient_identifier=invalid_nhs_num)

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue(invalid_nhs_num in body["issue"][0]["diagnostics"])

    @mock_aws
    @patch("fhir_controller.sqs_client.send_message")
    def test_invalid_nhs_number_batch(self, mock_send_message):
        """it should handle ValidationError when patient doesn't exist"""
        imms = Immunization.construct()
        aws_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:create",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "create",
            },
            "body": imms.json(),
        }
        invalid_nhs_num = "a-bad-id"
        self.service.create_immunization.side_effect = InvalidPatientId(patient_identifier=invalid_nhs_num)

        response = self.controller.create_immunization(aws_event)
        mock_send_message.assert_called_once()

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue(invalid_nhs_num in body["issue"][0]["diagnostics"])

    @mock_aws
    @patch("fhir_controller.sqs_client.send_message")
    def test_duplicate_record_batch(self, mock_send_message):
        """it should handle ValidationError when patient doesn't exist"""
        imms = Immunization.construct()
        aws_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:create",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "create"
            },
            "body": imms.json(),
        }
        self.service.create_immunization.side_effect = IdentifierDuplicationError(identifier="test")

        response = self.controller.create_immunization(aws_event)
        mock_send_message.assert_called_once()
        self.assertEqual(response["statusCode"], 422)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue("test" in body["issue"][0]["diagnostics"])

    def test_pds_unhandled_error(self):
        """it should respond with 500 if PDS returns error"""
        imms = Immunization.construct()
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": imms.json(),
        }
        self.service.create_immunization.side_effect = UnhandledResponseError(response={}, message="a message")

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(500, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    @mock_aws
    @patch("fhir_controller.sqs_client.send_message")
    def test_pds_unhandled_error_batch(self, mock_send_message):
        """it should respond with 500 if PDS returns error"""
        imms = Immunization.construct()
        aws_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:create",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "create"
            },
            "body": imms.json(),
        }
        self.service.create_immunization.side_effect = UnhandledResponseError(response={}, message="a message")

        response = self.controller.create_immunization(aws_event)
        mock_send_message.assert_called_once()
        self.assertEqual(500, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")


class TestUpdateImmunization(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    def test_update_immunization(self):
        """it should update Immunization"""
        imms_id = "valid-id"
        imms = '{"id": "valid-id"}'
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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
            imms_id, json.loads(imms), 1, "COVID19:update", "Test", False
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    @patch("fhir_controller.sqs_client.send_message")
    def test_update_immunization_etag_missing(self, mock_sqs_message):
        """it should update Immunization"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
            "body": imms,
            "pathParameters": {"id": imms_id},
        }
        response = self.controller.update_immunization(aws_event)
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 400)
        self.assertIn(
            "Validation errors: Immunization resource version not specified in the request headers",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    @patch("fhir_controller.sqs_client.send_message")
    def test_update_immunization_duplicate(self, mock_sqs_message):
        """it should not update the Immunization record"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
            "body": imms,
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
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 422)

    def test_update_immunization_UnauthorizedVaxError(self):
        """it should not update the Immunization record"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
            "body": imms,
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
        self.assertEqual(response["statusCode"], 403)

    def test_update_immunization_UnauthorizedVaxError_check_for_non_batch(self):
        """it should not update the Immunization record"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "", "SupplierSystem": "Test"},
            "body": imms,
            "pathParameters": {"id": imms_id},
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_update_immunization_Unauthorizedsystem_check_for_non_batch(self):
        """it should not update the Immunization record"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:UPDATE", "SupplierSystem": ""},
            "body": imms,
            "pathParameters": {"id": imms_id},
        }

        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.sqs_client.send_message")
    def test_update_immunization_for_batch_existing_record_is_none(self, mock_sqs_message):
        """it should update Immunization"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
            "body": imms,
            "pathParameters": {"id": imms_id},
        }
        self.service.update_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"
        self.service.get_immunization_by_id_all.return_value = None
        response = self.controller.update_immunization(aws_event)

        # self.service.update_immunization.assert_called_once_with(imms_id, json.loads(imms), 1, "COVID19:update", "Test", False)
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 404)
        self.assertIn(
            "The requested immunization resource with id:valid-id was not found.",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    def test_unauthorised_update_immunization(self):
        """it should return authorization error"""
        aws_event = {"body": ()}
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.sqs_client.send_message")
    def test_update_immunization_for_batch(self, mock_send_message):
        """it should update Immunization"""
        imms_id = "valid-id"
        imms = {"id": "valid-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
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

        expected_message_body = json.dumps(
            {
                "statusCode": 200,
                "headers": {},
                "file_key": aws_event["headers"]["file_key"],
                "row_id": aws_event["headers"]["row_id"],
                "created_at_formatted_string": aws_event["headers"]["created_at_formatted_string"],
                "local_id": aws_event["headers"]["local_id"],
                "operation_requested": "update"
            }
        )

        mock_send_message.assert_called_once_with(
            QueueUrl="Queue_url", MessageBody=expected_message_body, MessageGroupId=aws_event["headers"]["file_key"]
        )
        self.service.update_immunization.assert_called_once_with(imms_id, imms, 1, None, "Test", True)
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_update_immunization_for_invalid_version(self):
        """it should not update Immunization"""
        imms = '{"id": "valid-id"}'
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": "ajjsajj", "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
            "body": imms,
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

    def test_update_deletedat_immunization_with_version(self):
        """it should reinstate deletedat Immunization"""
        imms = '{"id": "valid-id"}'
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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
            imms_id, json.loads(imms), 1, "COVID19:update", "Test", False
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_update_deletedat_immunization_without_version(self):
        """it should reinstate deletedat Immunization"""
        imms = '{"id": "valid-id"}'
        imms_id = "valid-id"
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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
            imms_id, json.loads(imms), 1, "COVID19:update", "Test", False
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_update_record_exists(self):
        """it should return not-found OperationOutcome if ID doesn't exist"""
        # Given
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)

        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, "COVID19:update")

        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    def test_validation_error(self):
        """it should return 400 if Immunization is invalid"""
        imms = '{"id": "valid-id"}'
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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

    @patch("fhir_controller.sqs_client.send_message")
    def test_validation_error_for_batch(self, mock_send_message):
        """it should return 400 if Immunization is invalid"""
        imms = '{"id": 123}'
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
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
        mock_send_message.assert_called_once()
        self.assertEqual(400, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_validation_superseded_number_to_give_bad_request_for_update_immunization(self):
        """it should return 400 if Immunization has superseded nhs number."""
        update_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.update_immunization.return_value = None, update_result
        req_imms = '{"id": "valid-id"}'
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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

    def test_validation_identifier_to_give_bad_request_for_update_immunization(self):
        """it should return 400 if Identifier system and value  doesn't match with the stored content."""
        req_imms = '{"id": "valid-id"}'
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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

    def test_version_mismatch_for_update_immunization(self):
        """it should return 400 if resource version mismatch"""
        update_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.update_immunization.return_value = None, update_result
        req_imms = '{"id": "valid-id"}'
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "SupplierSystem": "Test"},
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

    def test_inconsistent_imms_id(self):
        """Immunization[id] should be the same as request"""
        bad_json = '{"id": "a-diff-id"}'
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": bad_json,
            "pathParameters": {"id": "an-id"},
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn(
            "The provided immunization id:an-id doesn't match with the content of the request body",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    @patch("fhir_controller.sqs_client.send_message")
    def test_inconsistent_imms_id_for_batch(self, mock_sqs_message):
        """Immunization[id] should be the same as request"""
        bad_json = {"id": "a-diff-id"}
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
            "body": bad_json,
            "pathParameters": {"id": "an-id"},
        }
        response = self.controller.update_immunization(aws_event)
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 400)
        self.assertIn(
            "The provided immunization id:an-id doesn't match with the content of the request body",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    def test_missing_imms_id(self):
        """Immunization[id] should exist and be the same as request"""
        bad_json = "{}"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": bad_json,
            "pathParameters": {"id": "an-id"},
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn(
            "The provided immunization id:an-id doesn't match with the content of the request body",
            json.loads(response["body"])["issue"][0]["diagnostics"],
        )

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = '{foo: "bar"}'
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "body": bad_json,
            "pathParameters": {"id": "valid-id"},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(self.service.update_immunization.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_imms_id(self):
        """it should validate lambda's Immunization id"""
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "SupplierSystem": "Test"},
            "pathParameters": {"id": "invalid %$ id"},
        }

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(self.service.update_immunization.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    @patch("fhir_controller.sqs_client.send_message")
    def test_validate_imms_id_for_batch(self, mock_sqs_message):
        """it should validate lambda's Immunization id"""
        valid_json = '{"foo": "bar"}'
        aws_event = {
            "headers": {
                "E-Tag": 1,
                "VaccineTypePermissions": "COVID19:update",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "update"
            },
            "pathParameters": {"id": "invalid %$ id"},
            "body": valid_json,
        }

        response = self.controller.update_immunization(aws_event)
        mock_sqs_message.assert_called_once()
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

    @patch("fhir_controller.sqs_client.send_message")
    def test_validate_imms_id_for_batch(self, mock_sqs_message):
        """it should validate lambda's Immunization id"""
        invalid_id = {
            "pathParameters": {"id": "invalid %$ id"},
            "headers": {
                "VaccineTypePermissions": "COVID19:delete",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "delete"
            },
        }

        response = self.controller.delete_immunization(invalid_id)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_delete_immunization_UnauthorizedVaxError_check_for_non_batch(self):
        """it should not delete the Immunization record"""
        imms_id = "an-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "", "SupplierSystem": "Test"},
            "pathParameters": {"id": imms_id},
        }
        response = self.controller.delete_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_unauthorised_delete_immunization(self):
        """it should return authorization error"""
        aws_event = {"body": ()}
        response = self.controller.delete_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_delete_immunization(self):
        # Given
        imms_id = "an-id"
        self.service.delete_immunization.return_value = Immunization.construct()
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "SupplierSystem": "Test"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.service.delete_immunization.assert_called_once_with(imms_id, "COVID19:delete", "Test", False)

        self.assertEqual(response["statusCode"], 204)
        self.assertTrue("body" not in response)

    @patch("fhir_controller.sqs_client.send_message")
    def test_delete_immunization_unauthorised_vax(self, mock_sqs_message):
        # Given
        imms_id = "an-id"
        self.service.delete_immunization.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:delete",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "delete"
            },
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        mock_sqs_message.assert_called_once()
        self.assertEqual(response["statusCode"], 403)

    @patch("fhir_controller.sqs_client.send_message")
    def test_delete_immunization_for_batch(self, mock_send_message):
        # Given
        imms_id = "an-id"
        self.service.delete_immunization.return_value = Immunization.construct()
        lambda_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:delete",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "delete"
            },
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.service.delete_immunization.assert_called_once_with(imms_id, None, "Test", True)
        expected_message_body = json.dumps(
            {
                "statusCode": 204,
                "headers": {},
                "file_key": lambda_event["headers"]["file_key"],
                "row_id": lambda_event["headers"]["row_id"],
                "created_at_formatted_string": lambda_event["headers"]["created_at_formatted_string"],
                "local_id": lambda_event["headers"]["local_id"],
                "operation_requested": "delete"
            }
        )

        mock_send_message.assert_called_once_with(
            QueueUrl="Queue_url", MessageBody=expected_message_body, MessageGroupId=lambda_event["headers"]["file_key"]
        )
        self.assertEqual(response["statusCode"], 204)
        self.assertTrue("body" not in response)

    def test_immunization_exception_not_found(self):
        """it should return not-found OperationOutcome if service throws ResourceNotFoundError"""
        # Given
        error = ResourceNotFoundError(resource_type="Immunization", resource_id="an-error-id")
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "SupplierSystem": "Test"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    @patch("fhir_controller.sqs_client.send_message")
    def test_immunization_exception_not_found_for_batch(self, mock_send_message):
        """it should return not-found OperationOutcome if service throws ResourceNotFoundError"""
        # Given
        error = ResourceNotFoundError(resource_type="Immunization", resource_id="an-error-id")
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:delete",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "delete"
            },
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)
        mock_send_message.assert_called_once()
        # Then
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    def test_immunization_unhandled_error(self):
        """it should return server-error OperationOutcome if service throws UnhandledResponseError"""
        # Given
        error = UnhandledResponseError(message="a message", response={})
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "SupplierSystem": "Test"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "exception")

    @patch("fhir_controller.sqs_client.send_message")
    def test_immunization_unhandled_error_for_batch(self, mock_send_message):
        """it should return server-error OperationOutcome if service throws UnhandledResponseError"""
        # Given
        error = UnhandledResponseError(message="a message", response={})
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {
                "VaccineTypePermissions": "COVID19:delete",
                "SupplierSystem": "Imms-Batch-App",
                "BatchSupplierSystem": "Test",
                "file_key": "test",
                "row_id": "123",
                "created_at_formatted_string": "2020-01-01",
                "local_id": ValidValues.test_local_id,
                "operation_requested": "delete"
            },
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        mock_send_message.assert_called_once()
        self.assertEqual(response["statusCode"], 500)
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

    def test_get_search_immunizations(self):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [(f"{self.patient_identifier_key}", f"{self.patient_identifier_valid_value}")]
        )
        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "COVID19:search",
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
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_get_search_immunizations_vax_permission_check(self):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 403)

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search(self):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": "flu:search"},
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

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_400(self):
        """it should return 400 as the the request is having invalid vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = "FLUE"

        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": "flu:search"},
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

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_403(self):
        """it should return 403 as the user doesnt have vaccinetype permission"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": ""},
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_get_search_immunizations_unauthorized(self):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
        params = f"{self.immunization_target_key}={vaccine_type}&" + urllib.parse.urlencode(
            [(f"{self.patient_identifier_key}", f"{self.patient_identifier_valid_value}")]
        )
        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": "FLU:search"},
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 403)

    def test_post_search_immunizations(self):
        """it should search based on patient_identifier and immunization_target"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
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
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "COVID19:search",
            },
            "body": base64_encoded_body,
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_post_search_immunizations_for_unauthorized_vaccine_type_search(self):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
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
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": "flu:search"},
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

    def test_post_search_immunizations_for_unauthorized_vaccine_type_search_403(self):
        """it should return 403 as the user doesnt have vaccinetype permission"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
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
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "VaccineTypePermissions": ""},
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

    def test_search_immunizations_returns_400_on_passing_superseded_nhs_number(self):
        "This method should return 400 as input paramter has superseded nhs number."
        search_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "COVID19:search",
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
        "This method should return 200 but remove the data which has status as not done."
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle
        vaccine_type = VaccineTypes().all[0]
        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "COVID19:search",
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
        self.service.search_immunizations.return_value = search_result
        vaccine_type = VaccineTypes().all[0]
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
                "VaccineTypePermissions": "COVID19:search",
            },
            "httpMethod": "POST",
        }

        self.controller.search_immunizations(lambda_event)

        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
