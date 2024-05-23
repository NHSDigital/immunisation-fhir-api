import base64
import urllib

import json
import unittest
import uuid

from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.immunization import Immunization
from unittest.mock import create_autospec, ANY, patch, Mock
from urllib.parse import urlencode
from authorization import Authorization
from fhir_controller import FhirController
from fhir_service import FhirService, UpdateOutcome
from models.errors import (
    ResourceNotFoundError,
    UnhandledResponseError,
    InvalidPatientId,
    CustomValidationError,
    ParameterException,
)
from tests.immunization_utils import create_covid_19_immunization
from mappings import VaccineTypes
from parameter_parser import patient_identifier_system, process_search_params


class TestFhirController(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
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
        lambda_event = {"pathParameters": {"id": imms_id}}

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id)

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Immunization")

    def test_not_found(self):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {"pathParameters": {"id": imms_id}}

        # When
        response = self.controller.get_immunization_by_id(lambda_event)

        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id)

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
        aws_event = {"body": imms.json()}
        self.service.create_immunization.return_value = imms

        response = self.controller.create_immunization(aws_event)

        imms_obj = json.loads(aws_event["body"])
        self.service.create_immunization.assert_called_once_with(imms_obj)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{imms_id}"))

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = '{foo: "bar"}'
        aws_event = {"body": bad_json}

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_create_bad_request_for_superseded_number_for_create_immunization(self):
        """it should return 400 if json has superseded nhs number."""
        create_result = {"diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"}
        self.service.create_immunization.return_value = create_result
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {"body": imms.json()}
        # When
        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome") 

    def test_invalid_nhs_number(self):
        """it should handle ValidationError when patient doesn't exist"""
        imms = Immunization.construct()
        aws_event = {"body": imms.json()}
        invalid_nhs_num = "a-bad-id"
        self.service.create_immunization.side_effect = InvalidPatientId(patient_identifier=invalid_nhs_num)

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue(invalid_nhs_num in body["issue"][0]["diagnostics"])

    def test_pds_unhandled_error(self):
        """it should respond with 500 if PDS returns error"""
        imms = Immunization.construct()
        aws_event = {"body": imms.json()}
        self.service.create_immunization.side_effect = UnhandledResponseError(response={}, message="a message")

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(500, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")


class TestUpdateImmunization(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.controller = FhirController(self.authorizer, self.service)

    def test_create_immunization(self):
        """it should update Immunization"""
        imms = "{}"
        imms_id = "valid-id"
        aws_event = {"body": imms, "pathParameters": {"id": imms_id}}
        self.service.update_immunization.return_value = UpdateOutcome.UPDATE, "value doesn't matter"

        response = self.controller.update_immunization(aws_event)

        self.service.update_immunization.assert_called_once_with(imms_id, json.loads(imms))
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_create_new_imms(self):
        """it should return 201 if update creates a new record"""
        req_imms = "{}"
        path_id = "valid-id"
        aws_event = {"body": req_imms, "pathParameters": {"id": path_id}}

        new_id = "newly-created-id"
        created_imms = create_covid_19_immunization(imms_id=new_id)
        self.service.update_immunization.return_value = UpdateOutcome.CREATE, created_imms

        # When
        response = self.controller.update_immunization(aws_event)

        # Then
        self.service.update_immunization.assert_called_once_with(path_id, json.loads(req_imms))
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{new_id}"))

    def test_validation_error(self):
        """it should return 400 if Immunization is invalid"""
        imms = "{}"
        aws_event = {"body": imms, "pathParameters": {"id": "valid-id"}}
        self.service.update_immunization.side_effect = CustomValidationError(message="invalid")

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(400, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_validation_superseded_number_to_give_bad_request_for_update_immunization(self):
        """it should return 400 if Immunization has superseded nhs number."""
        update_result = {"diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"}
        self.service.update_immunization.return_value = None,update_result
        req_imms = "{}"
        path_id = "valid-id"
        aws_event = {"body": req_imms, "pathParameters": {"id": path_id}}
        # When
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")      

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = '{foo: "bar"}'
        aws_event = {"body": bad_json, "pathParameters": {"id": "valid-id"}}

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(self.service.update_immunization.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_validate_imms_id(self):
        """it should validate lambda's Immunization id"""
        invalid_id = {"pathParameters": {"id": "invalid %$ id"}}

        response = self.controller.update_immunization(invalid_id)

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
        invalid_id = {"pathParameters": {"id": "invalid %$ id"}}

        response = self.controller.delete_immunization(invalid_id)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_delete_immunization(self):
        # Given
        imms_id = "an-id"
        self.service.delete_immunization.return_value = Immunization.construct()
        lambda_event = {"pathParameters": {"id": imms_id}}

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.service.delete_immunization.assert_called_once_with(imms_id)

        self.assertEqual(response["statusCode"], 204)
        self.assertTrue("body" not in response)

    def test_immunization_exception_not_found(self):
        """it should return not-found OperationOutcome if service throws ResourceNotFoundError"""
        # Given
        error = ResourceNotFoundError(resource_type="Immunization", resource_id="an-error-id")
        self.service.delete_immunization.side_effect = error
        lambda_event = {"pathParameters": {"id": "a-non-existing-id"}}

        # When
        response = self.controller.delete_immunization(lambda_event)

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
        lambda_event = {"pathParameters": {"id": "a-non-existing-id"}}

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
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
            "multiValueQueryStringParameters": {
                self.immunization_target_key: [vaccine_type],
                self.patient_identifier_key: [self.patient_identifier_valid_value],
            }
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
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
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
        search_result = {"diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"}
        self.service.search_immunizations.return_value = search_result

        vaccine_type = VaccineTypes().all[0]
        lambda_event = {"multiValueQueryStringParameters": {
            self.immunization_target_key: [vaccine_type],
            self.patient_identifier_key: [self.patient_identifier_valid_value]
        }}

        # When
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")    

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
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "httpMethod": "POST",
        }

        self.controller.search_immunizations(lambda_event)

        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
