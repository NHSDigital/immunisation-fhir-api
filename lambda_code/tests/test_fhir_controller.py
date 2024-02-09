import json
import unittest
import uuid
from unittest.mock import create_autospec
from urllib.parse import urlencode
from fhir.resources.R4B.immunization import Immunization
from fhir.resources.R4B.bundle import Bundle
import base64
from fhir_controller import FhirController, get_service_url
from fhir_service import FhirService, UpdateOutcome
from models.errors import ResourceNotFoundError, UnhandledResponseError, InvalidPatientId, CoarseValidationError
from tests.immunization_utils import create_an_immunization


def _create_a_post_event(body: str) -> dict:
    return {"version": "2.0", "routeKey": "POST /event", "rawPath": "/jaho3/event", "rawQueryString": "",
            "headers": {"accept-encoding": "br,deflate,gzip,x-gzip", "content-length": "688",
                        "content-type": "application/fhir+json", "host": "jaho3.imms.dev.api.platform.nhs.uk",
                        "user-agent": "Apache-HttpClient/4.5.14 (Java/17.0.8.1)",
                        "x-amzn-trace-id": "Root=1-6556ab07-72760aca0fdf068e5997f65a",
                        "x-forwarded-for": "81.110.196.79", "x-forwarded-port": "443", "x-forwarded-proto": "https"},
            "requestContext": {"accountId": "790083933819", "apiId": "bgllbuiz2i",
                               "domainName": "jaho3.imms.dev.api.platform.nhs.uk", "domainPrefix": "jaho3",
                               "http": {"method": "POST", "path": "/jaho3/event", "protocol": "HTTP/1.1",
                                        "sourceIp": "81.110.196.79",
                                        "userAgent": "Apache-HttpClient/4.5.14 (Java/17.0.8.1)"},
                               "requestId": "Og-pShuvLPEEM1Q=", "routeKey": "POST /event", "stage": "jaho3",
                               "time": "16/Nov/2023:23:51:35 +0000", "timeEpoch": 1700178695954},
            "body": "{\n  \"resourceType\": \"Immunization\",\n  \"id\": \"e045626e-4dc5-4df3-bc35-da25263f901e\",\n  \"identifier\": [\n    {\n      \"system\": \"https://supplierABC/ODSCode\",\n      \"value\": \"e045626e-4dc5-4df3-bc35-da25263f901e\"\n    }\n  ],\n  \"status\": \"completed\",\n  \"vaccineCode\": {\n    \"coding\": [\n      {\n        \"system\": \"http://snomed.info/sct\",\n        \"code\": \"39114911000001105\",\n        \"display\": \"some text\"\n      }\n    ]\n  },\n  \"patient\": {\n    \"reference\": \"urn:uuid:124fcb63-669c-4a3c-af2b-caf55de167ec\",\n    \"type\": \"Patient\",\n    \"identifier\": {\n      \"system\": \"https://fhir.nhs.uk/Id/nhs-number\",\n      \"value\": \"9000000009\"\n    }\n  },\n  \"occurrenceDateTime\": \"2020-12-14T10:08:15+00:00\"\n}",
            "isBase64Encoded": False}


class TestFhirController(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)

    def test_create_response(self):
        """it should return application/fhir+json with correct status code"""
        body = {"message": "a body"}
        res = self.controller.create_response(42, body)
        headers = res["headers"]

        self.assertEqual(res["statusCode"], 42)
        self.assertDictEqual(headers, {
            "Content-Type": "application/fhir+json",
        })
        self.assertDictEqual(json.loads(res["body"]), body)

    def test_no_body_no_header(self):
        res = self.controller.create_response(42)
        self.assertEqual(res["statusCode"], 42)
        self.assertDictEqual(res["headers"], {})
        self.assertTrue("body" not in res)

    def test_get_service_url(self):
        """it should create service url"""
        env = "int"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://{env}.api.service.nhs.uk/{base_path}")
        # default should be internal-dev
        env = "it-does-not-exist"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://internal-dev.api.service.nhs.uk/{base_path}")
        # prod should not have subdomain
        env = "prod"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://api.service.nhs.uk/{base_path}")
        # any other env should fall back to internal-dev (like pr-xx or per-user)
        env = "pr-42"
        base_path = "my-base-path"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://internal-dev.api.service.nhs.uk/{base_path}")


class TestFhirControllerGetImmunizationById(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)

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
        self.controller = FhirController(self.service)

    def test_create_immunization(self):
        """it should create Immunization and return resource's location"""
        imms_id = str(uuid.uuid4())
        imms = create_an_immunization(imms_id)
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
        bad_json = "{foo: \"bar\"}"
        aws_event = {"body": bad_json}

        response = self.controller.create_immunization(aws_event)

        self.assertEqual(self.service.get_immunization_by_id.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_invalid_nhs_number(self):
        """it should handle ValidationError when patient doesn't exist"""
        imms = Immunization.construct()
        aws_event = {"body": imms.json()}
        invalid_nhs_num = "a-bad-id"
        self.service.create_immunization.side_effect = InvalidPatientId(nhs_number=invalid_nhs_num)

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
        self.controller = FhirController(self.service)

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
        created_imms = create_an_immunization(imms_id=new_id)
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
        self.service.update_immunization.side_effect = CoarseValidationError(message="invalid")

        response = self.controller.update_immunization(aws_event)

        self.assertEqual(400, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = "{foo: \"bar\"}"
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
        self.controller = FhirController(self.service)

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
        self.assertEqual(body["issue"][0]["code"], "internal-server-error")


class TestSearchImmunizations(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.nhs_search_param="-nhsNumber"
        self.disease_type_search_param="-diseaseType"

    def test_get_search_immunizations(self):
        """it should search based on nhsNumber and diseaseType"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        nhs_number = "an-patient-id"
        disease_type = "a-disease-type"
        params=f"{self.nhs_search_param}={nhs_number}&{self.disease_type_search_param}={disease_type}"
        lambda_event = {"queryStringParameters": {
            self.disease_type_search_param: disease_type,
            self.nhs_search_param: nhs_number
        }}

        # When
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.service.search_immunizations.assert_called_once_with(nhs_number, disease_type,params)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_post_search_immunizations(self):
        """it should search based on nhsNumber and diseaseType"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        nhs_number = "an-patient-id"
        disease_type = "a-disease-type"
        params=f"{self.nhs_search_param}={nhs_number}&{self.disease_type_search_param}={disease_type}"
        # Construct the application/x-www-form-urlencoded body
        body = {
            self.nhs_search_param: nhs_number,
            self.disease_type_search_param: disease_type
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": base64_encoded_body
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.search_immunizations.assert_called_once_with(nhs_number, disease_type,params)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_post_empty_body_search_immunizations(self):
        """it should return bad request if nhsNumber and diseaseType are neither given in body nor in queryParams"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result
        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")


    def test_repeated_same_params_search_immunizations(self):
        """it should search based on nhsNumber and diseaseType irresepctive of their repition in params and body"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        nhs_number = "an-patient-id"
        disease_type = "a-disease-type"
        params=f"{self.nhs_search_param}={nhs_number}&{self.disease_type_search_param}={disease_type}"
        # Construct the application/x-www-form-urlencoded body
        body = {
            self.nhs_search_param: nhs_number,
            self.disease_type_search_param: disease_type
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": base64_encoded_body,
            "queryStringParameters":{self.disease_type_search_param: disease_type,
            self.nhs_search_param: nhs_number},
            
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.search_immunizations.assert_called_once_with(nhs_number, disease_type,params)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_mixed_params_search_immunizations(self):
        """it should search based on nhsNumber in body and diseaseType in params"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        nhs_number = "an-patient-id"
        disease_type = "a-disease-type"
        params=f"{self.nhs_search_param}={nhs_number}&{self.disease_type_search_param}={disease_type}"
        # Construct the application/x-www-form-urlencoded body
        body = {
            self.nhs_search_param: nhs_number
        }
        encoded_body = urlencode(body)
        # Base64 encode the body
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        # Construct the lambda event
        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": base64_encoded_body,
            "queryStringParameters":{self.disease_type_search_param: disease_type},
            
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.search_immunizations.assert_called_once_with(nhs_number, disease_type,params)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Bundle")

    def test_repeated_different_params_search_immunizations(self):
        """it should return bad request if nhsNumber or diseaseType are different in params and body"""
        search_result = Bundle.construct()
        self.service.search_immunizations.return_value = search_result

        nhs_number1 = "an-patient-id"
        disease_type1 = "a-disease-type"
        nhs_number2 = "an-patient-id2"
        disease_type2 = "a-disease-type2"
        body = {
            self.nhs_search_param: nhs_number2,
            self.disease_type_search_param: disease_type2
        }
        encoded_body = urlencode(body)
        base64_encoded_body = base64.b64encode(encoded_body.encode("utf-8")).decode("utf-8")

        lambda_event = {
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": base64_encoded_body,
            "queryStringParameters":{self.disease_type_search_param: disease_type1,
            self.nhs_search_param: nhs_number1}
        }
        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_nhs_number_is_mandatory(self):
        """nhsNumber is a mandatory query param"""
        lambda_event = {"queryStringParameters": {
            self.disease_type_search_param: "a-disease-type",
        }}

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(self.service.search_immunizations.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")

    def test_diseaseType_is_mandatory(self):
        """diseaseType is a mandatory query param"""
        lambda_event = {"queryStringParameters": {
            self.nhs_search_param: "an-id",
        }}

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(self.service.search_immunizations.call_count, 0)
        self.assertEqual(response["statusCode"], 400)
        outcome = json.loads(response["body"])
        self.assertEqual(outcome["resourceType"], "OperationOutcome")
