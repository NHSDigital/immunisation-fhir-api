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
    UnauthorizedSystemError,
)
from tests.immunization_utils import create_covid_19_immunization, create_covid_19_immunization_dict
from mappings import VaccineTypes
from parameter_parser import patient_identifier_system, process_search_params
from tests.utils.generic_utils import load_json_data


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
            "headers": {"VaccineTypePermissions": "COVID19:read", "ApplicationId": "TestApp"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.get_immunization_by_id(lambda_event)
        # Then
        self.service.get_immunization_by_id.assert_called_once_with(imms_id, "COVID19:read")

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "Immunization")

    def test_not_found(self):
        """it should return not-found OperationOutcome if it doesn't exist"""
        # Given
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {
            "headers": {"VaccineTypePermissions": "COVID19:read", "ApplicationId": "TestApp"},
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
            "headers": {"VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
            "body": imms.json(),
        }
        self.service.create_immunization.return_value = imms

        response = self.controller.create_immunization(aws_event)

        imms_obj = json.loads(aws_event["body"])
        self.service.create_immunization.assert_called_once_with(imms_obj, "COVID19:create", "TestApp")
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue("body" not in response)
        self.assertTrue(response["headers"]["Location"].endswith(f"Immunization/{imms_id}"))

    def test_unauthorised_create_immunization(self):
        """it should return authorization error"""
        imms_id = str(uuid.uuid4())
        imms = create_covid_19_immunization(imms_id)
        aws_event = {"body": imms.json()}
        response = self.controller.create_immunization(aws_event)
        self.assertEqual(response["statusCode"], 403)

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = '{foo: "bar"}'
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
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
            "headers": {"VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
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
            "headers": {"VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
            "body": imms.json(),
        }
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
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
            "body": imms.json(),
        }
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

    def test_update_immunization(self):
        """it should update Immunization"""
        imms = "{}"
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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

        self.service.update_immunization.assert_called_once_with(imms_id, json.loads(imms), 1, "COVID19:update")
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_update_immunization_for_invalid_version(self):
        """it should not update Immunization"""
        imms = "{}"
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": "ajjsajj", "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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
        imms = "{}"
        imms_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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

        self.service.reinstate_immunization.assert_called_once_with(imms_id, json.loads(imms), 1, "COVID19:update")
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_update_deletedat_immunization_without_version(self):
        """it should reinstate deletedat Immunization"""
        imms = "{}"
        imms_id = "valid-id"
        aws_event = {
            "headers": {"VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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

        self.service.reinstate_immunization.assert_called_once_with(imms_id, json.loads(imms), 1, "COVID19:update")
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" not in response)

    def test_update_record_exists(self):
        """it should return not-found OperationOutcome if ID doesn't exist"""
        # Given
        imms_id = "a-non-existing-id"
        self.service.get_immunization_by_id.return_value = None
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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
        imms = "{}"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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

    def test_validation_superseded_number_to_give_bad_request_for_update_immunization(self):
        """it should return 400 if Immunization has superseded nhs number."""
        update_result = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value does not exists"
        }
        self.service.update_immunization.return_value = None, update_result
        req_imms = "{}"
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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

    def test_validation_update_for_unauthorized_system(self):
        """it should return 403 for unauthorized system"""
        req_imms = "{}"
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
            "body": req_imms,
            "pathParameters": {"id": path_id},
        }
        self.service.get_immunization_by_id_all.return_value = {
            "diagnostics": "Unauthorized system",
            "error": "Unauthorized",
        }
        # When
        response = self.controller.update_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_validation_identifier_to_give_bad_request_for_update_immunization(self):
        """it should return 400 if Identifier system and value  doesn't match with the stored content."""
        req_imms = "{}"
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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
        req_imms = "{}"
        path_id = "valid-id"
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:update", "ApplicationId": "TestApp"},
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

    def test_consistent_imms_id(self):
        """Immunization[id] should be the same as request"""
        bad_json = '{"id": "a-diff-id"}'
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
            "body": bad_json,
            "pathParameters": {"id": "an-id"},
        }
        response = self.controller.update_immunization(aws_event)
        self.assertEqual(response["statusCode"], 400)

    def test_malformed_resource(self):
        """it should return 400 if json is malformed"""
        bad_json = '{foo: "bar"}'
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
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
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:create", "ApplicationId": "TestApp"},
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
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "ApplicationId": "TestApp"},
            "pathParameters": {"id": imms_id},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.service.delete_immunization.assert_called_once_with(imms_id, "COVID19:delete", "TestApp")

        self.assertEqual(response["statusCode"], 204)
        self.assertTrue("body" not in response)

    def test_immunization_exception_not_found(self):
        """it should return not-found OperationOutcome if service throws ResourceNotFoundError"""
        # Given
        error = ResourceNotFoundError(resource_type="Immunization", resource_id="an-error-id")
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "ApplicationId": "TestApp"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 404)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertEqual(body["issue"][0]["code"], "not-found")

    def test_validation_delete_for_unauthorized_system(self):
        """it should return 403 for unauthorized system"""
        error = UnauthorizedSystemError()
        self.service.delete_immunization.side_effect = error
        aws_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "ApplicationId": "TestApp"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

        # When
        response = self.controller.delete_immunization(aws_event)

        self.assertEqual(response["statusCode"], 403)
        body = json.loads(response["body"])
        self.assertEqual(body["resourceType"], "OperationOutcome")

    def test_immunization_unhandled_error(self):
        """it should return server-error OperationOutcome if service throws UnhandledResponseError"""
        # Given
        error = UnhandledResponseError(message="a message", response={})
        self.service.delete_immunization.side_effect = error
        lambda_event = {
            "headers": {"E-Tag": 1, "VaccineTypePermissions": "COVID19:delete", "ApplicationId": "TestApp"},
            "pathParameters": {"id": "a-non-existing-id"},
        }

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
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "COVID19:search",
                "ApplicationId": "TestApp",
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

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search(self):
        """it should return 200 and contains warning operation outcome as the user is not having authorization for one of the vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "flu:search",
                "ApplicationId": "TestApp",
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
        self.assertTrue(operation_outcome_present, "OperationOutcome resource is not present in the response")

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_400(self):
        """it should return 400 as the the request is having invalid vaccine type"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = "FLUE"

        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "flu:search",
                "ApplicationId": "TestApp",
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

    def test_get_search_immunizations_for_unauthorized_vaccine_type_search_403(self):
        """it should return 403 as the user doesnt have vaccinetype permission"""
        search_result = load_json_data("sample_immunization_response _for _not_done_event.json")
        bundle = Bundle.parse_obj(search_result)
        self.service.search_immunizations.return_value = bundle

        vaccine_type = VaccineTypes().all[0], VaccineTypes().all[1]
        vaccine_type = ",".join(vaccine_type)

        lambda_event = {
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "",
                "ApplicationId": "TestApp",
            },
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
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "FLU:search",
                "ApplicationId": "TestApp",
            },
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
                "ApplicationId": "TestApp",
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
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "flu:search",
                "ApplicationId": "TestApp",
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
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "flu:search",
                "ApplicationId": "TestApp",
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
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "VaccineTypePermissions": "",
                "ApplicationId": "TestApp",
            },
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
                "ApplicationId": "TestApp",
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
                "ApplicationId": "TestApp",
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
                "ApplicationId": "TestApp",
            },
            "httpMethod": "POST",
        }

        self.controller.search_immunizations(lambda_event)

        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, [vaccine_type], params, ANY, ANY
        )
