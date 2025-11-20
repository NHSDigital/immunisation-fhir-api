import base64
import copy
import datetime
import json
import unittest
import urllib
import urllib.parse
import uuid
from unittest.mock import ANY, Mock, create_autospec, patch

from fhir.resources.R4B.bundle import Bundle, BundleEntry, BundleLink
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.immunization import Immunization

from common.models.errors import (
    CustomValidationError,
    ResourceNotFoundError,
)
from controller.aws_apig_response_utils import create_response
from controller.fhir_controller import FhirController
from controller.parameter_parser import PATIENT_IDENTIFIER_SYSTEM
from models.errors import (
    UnauthorizedVaxError,
    UnhandledResponseError,
)
from repository.fhir_repository import ImmunizationRepository
from service.fhir_service import FhirService
from test_common.testing_utils.immunization_utils import create_covid_immunization


class TestFhirControllerBase(unittest.TestCase):
    """Base class for all tests to set up common fixtures"""

    def setUp(self):
        super().setUp()
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("controller.parameter_parser.get_redis_client")
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
    test_local_identifier = Identifier.construct(
        system="https://supplierABC/identifiers/vacc", value="f10b59b3-fc73-4616-99c9-9e882ab31184"
    )

    def setUp(self):
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_immunization_by_identifier_is_successful(self):
        """it should return a searchset Bundle containing the immunization if it exists"""
        # Given
        self.service.get_immunization_by_identifier.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "something"}))],
            link=[BundleLink.construct(relation="self", url="a-url")],
            type="searchset",
            total=1,
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": [f"{self.test_local_identifier.system}|{self.test_local_identifier.value}"],
                "_elements": ["id,meta"],
            },
            "body": None,
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            self.test_local_identifier, "test", {"meta", "id"}
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            response["body"],
            json.dumps(
                {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "link": [{"relation": "self", "url": "a-url"}],
                    "entry": [{"resource": {"resourceType": "Immunization", "id": "something"}}],
                    "total": 1,
                }
            ),
        )

    def test_get_immunization_by_identifier_is_successful_when_using_post_endpoint(self):
        """though not properly documented or really recommended, there is a /Immunization/_search POST endpoint which
        can be used for performing searches"""
        # Given
        self.service.get_immunization_by_identifier.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "something"}))],
            link=[BundleLink.construct(relation="self", url="a-url")],
            type="searchset",
            total=1,
        )
        form_data = {
            "identifier": f"{self.test_local_identifier.system}|{self.test_local_identifier.value}",
            "_elements": "id,meta",
        }
        url_encoded_test_str = urllib.parse.urlencode(form_data)
        lambda_event = {
            "headers": {"Content-Type": "xxx-www-form-urlencoded", "SupplierSystem": "test"},
            "multiValueQueryStringParameters": {},
            "body": base64.b64encode(url_encoded_test_str.encode("utf-8")).decode("utf-8"),
        }

        # When
        response = self.controller.search_immunizations(lambda_event, is_post_endpoint_req=True)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            self.test_local_identifier, "test", {"meta", "id"}
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            response["body"],
            json.dumps(
                {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "link": [{"relation": "self", "url": "a-url"}],
                    "entry": [{"resource": {"resourceType": "Immunization", "id": "something"}}],
                    "total": 1,
                }
            ),
        )

    def test_get_immunization_by_identifier_returns_no_entries_when_no_results(self):
        """it should return a searchset Bundle containing with no entries if the immunization does not exist"""
        # Given
        self.service.get_immunization_by_identifier.return_value = Bundle.construct(
            entry=[], link=[BundleLink.construct(relation="self", url="a-url")], type="searchset", total=1
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": [f"{self.test_local_identifier.system}|{self.test_local_identifier.value}"],
                "_elements": ["id,meta"],
            },
            "body": None,
        }

        # When
        response = self.controller.search_immunizations(lambda_event)
        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            self.test_local_identifier, "test", {"meta", "id"}
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            response["body"],
            json.dumps(
                {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "link": [{"relation": "self", "url": "a-url"}],
                    "entry": [],
                    "total": 1,
                }
            ),
        )

    def test_get_imms_by_identifier_returns_authorization_error_when_header_missing(self):
        """it should return a 403 status error when the header is not provided"""
        # Given
        lambda_event = {
            "multiValueQueryStringParameters": {
                "identifier": ["https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184"],
                "_elements": ["id,meta"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 403)

    def test_get_imms_by_identifier_returns_validation_error_when_no_params_provided(self):
        """it should return a 400 status error if the client provides no search parameters"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {},
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "No parameter provided. Search using either identifier or patient.identifier.",
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_params_are_duplicated(self):
        """it should return a 400 status error if the client provides the same parameter key multiple times"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": ["https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184"],
                "_elements": ["id,meta", "another_one_oops_use_commas_instead"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            'Parameters may not be duplicated. Use commas for "or".',
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_patient_identifier_params_provided(self):
        """it should return a 400 status error if the client also provides the patient.identifier parameter which is
        used for the separate NHS Number + vaccination type(s) search"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": ["https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184"],
                "patient.identifier": ["system|12345"],
                "_elements": ["id,meta"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Search parameter should have either identifier or patient.identifier",
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_unsupported_search_keys_provided(self):
        """it should return a 400 status error if the client provides search keys associated with the patient +
        vaccination type(s) search e.g. -date.from"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": ["https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184"],
                "-date.from": ["2025-01-01"],
                "_elements": ["id,meta"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Identifier search included patient.identifier search parameters",
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_multiple_identifiers_provided(self):
        """it should return a 400 status error if the client provides more than one identifier search param"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": [
                    "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184,"
                    + "https://supplierABC/identifiers/vacc|additional-search"
                ],
                "_elements": ["id,meta"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Search parameter identifier must have one value and must be in the format of "
            '"identifier.system|identifier.value" "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"',
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_no_identifier_provided_but_elements_present(self):
        """it should return a 400 status error if the client provides no identifier"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": [],
                "_elements": ["id,meta"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Search parameter _elements must have the following parameter: identifier",
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_identifier_invalid(self):
        """it should return a 400 status error if the client provides an invalid identifier i.e. not in the format of
        {system}|{identifier}"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": ["incorrect-format-identifier"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Search parameter identifier must have one value and must be in the format of "
            '"identifier.system|identifier.value" "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"',
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_get_imms_by_identifier_returns_validation_error_when_elements_invalid(self):
        """it should return a 400 status error if the client provides an _elements identifier i.e. not either meta, id
        or both"""
        # Given
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": [f"{self.test_local_identifier.system}|{self.test_local_identifier.value}"],
                "_elements": ["id,invalid"],
            },
            "body": None,
        }
        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "_elements must be one or more of the following: id,meta",
        )
        self.service.get_immunization_by_identifier.assert_not_called()

    def test_validate_imms_id_handles_exception_thrown_in_service_layer(self):
        """it should validate lambda's Immunization id"""
        # Given
        self.service.get_immunization_by_identifier.side_effect = UnauthorizedVaxError()
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                "identifier": [f"{self.test_local_identifier.system}|{self.test_local_identifier.value}"],
                "_elements": ["id,meta"],
            },
            "body": None,
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.service.get_immunization_by_identifier.assert_called_once_with(
            self.test_local_identifier, "test", {"meta", "id"}
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
    MOCK_REDIS_V2D_HKEYS = [
        "COVID",
        "FLU",
    ]

    patient_identifier_key = "patient.identifier"
    immunization_target_key = "-immunization.target"
    date_from_key = "-date.from"
    date_to_key = "-date.to"
    include_key = "_include"
    nhs_number_valid_value = "9000000009"
    patient_identifier_valid_value = f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number_valid_value}"
    test_lambda_event = {
        "headers": {
            "SupplierSystem": "test",
        },
        "multiValueQueryStringParameters": {
            immunization_target_key: ["COVID"],
            patient_identifier_key: [patient_identifier_valid_value],
            date_from_key: ["2000-01-01"],
            date_to_key: ["2024-01-01"],
            include_key: ["Immunization:patient"],
        },
    }

    def setUp(self):
        super().setUp()
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.mock_redis.hkeys.return_value = self.MOCK_REDIS_V2D_HKEYS
        self.mock_redis_getter.return_value = self.mock_redis

    def tearDown(self):
        patch.stopall()

    def test_search_immunizations_is_successful(self):
        """it should search based on patient_identifier and immunization_target"""
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "something"}))],
            link=[BundleLink.construct(relation="self", url="patient-search-url")],
            type="searchset",
            total=1,
        )
        vaccine_type = "COVID"
        lambda_event = {
            "headers": {
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
            self.nhs_number_valid_value, {vaccine_type}, "test", None, None, None
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            response["body"],
            json.dumps(
                {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "link": [{"relation": "self", "url": "patient-search-url"}],
                    "entry": [{"resource": {"resourceType": "Immunization", "id": "something"}}],
                    "total": 1,
                }
            ),
        )

    def test_search_immunizations_is_successful_when_using_the_post_endpoint(self):
        """though not properly documented or really recommended, there is a /Immunization/_search POST endpoint which
        can be used for performing patient and vacc type searches"""
        # Given
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "something"}))],
            link=[BundleLink.construct(relation="self", url="patient-search-url")],
            type="searchset",
            total=1,
        )
        vaccine_type = "COVID"
        form_data = {
            self.immunization_target_key: vaccine_type,
            self.patient_identifier_key: self.patient_identifier_valid_value,
        }
        url_encoded_test_str = urllib.parse.urlencode(form_data)
        lambda_event = {
            "headers": {"Content-Type": "xxx-www-form-urlencoded", "SupplierSystem": "test"},
            "multiValueQueryStringParameters": {},
            "body": base64.b64encode(url_encoded_test_str.encode("utf-8")).decode("utf-8"),
        }

        # When
        response = self.controller.search_immunizations(lambda_event, is_post_endpoint_req=True)

        # Then
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value, {vaccine_type}, "test", None, None, None
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            response["body"],
            json.dumps(
                {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "link": [{"relation": "self", "url": "patient-search-url"}],
                    "entry": [{"resource": {"resourceType": "Immunization", "id": "something"}}],
                    "total": 1,
                }
            ),
        )

    def test_search_immunizations_returns_a_validation_error_when_duplicate_params_provided(self):
        """it should return a 400 invalid error if the client provides duplicated keys in the parameters"""
        lambda_event = {
            "headers": {
                "SupplierSystem": "test",
            },
            "multiValueQueryStringParameters": {
                self.immunization_target_key: ["COVID"],
                self.patient_identifier_key: [self.patient_identifier_valid_value, "another-one"],
            },
        }

        # When
        response = self.controller.search_immunizations(lambda_event)

        # Then
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            'Parameters may not be duplicated. Use commas for "or".',
        )
        self.service.search_immunizations.assert_not_called()

    def test_search_immunizations_returns_a_validation_error_when_patient_identifier_invalid(self):
        """it should return a 400 invalid error for multiple invalid patient identifier scenarios"""
        test_cases = [
            (
                [f"{self.patient_identifier_valid_value},and-another-id"],
                "Search parameter patient.identifier must have one value.",
            ),
            (
                ["https://not-fhir.nhs.uk/Id/nhs-number|9000000009"],
                'patient.identifier must be in the format of "https://fhir.nhs.uk/Id/nhs-number|{NHS number}" e.g. '
                '"https://fhir.nhs.uk/Id/nhs-number|9000000009"',
            ),
            (
                ["https://fhir.nhs.uk/Id/nhs-number|9000450007"],
                "Search parameter patient.identifier must be a valid NHS number.",
            ),
        ]

        for test_patient_id, expected_error in test_cases:
            with self.subTest(msg=expected_error):
                test_lambda_event = copy.deepcopy(self.test_lambda_event)
                test_lambda_event["multiValueQueryStringParameters"]["patient.identifier"] = test_patient_id

                # When
                response = self.controller.search_immunizations(test_lambda_event)

                # Then
                self.assertEqual(response["statusCode"], 400)
                self.assertEqual(
                    json.loads(response["body"])["issue"][0]["diagnostics"],
                    expected_error,
                )
                self.service.search_immunizations.assert_not_called()

    def test_search_immunizations_returns_a_validation_error_when_immunization_target_invalid(self):
        """it should return a 400 invalid error for multiple invalid -immunization.target scenarios"""
        test_cases = [
            ([], "Search parameter -immunization.target must have one or more values."),
            (["COVID,FLU,CHICKENS"], "-immunization.target must be one or more of the following: COVID, FLU"),
        ]

        for test_patient_id, expected_error in test_cases:
            with self.subTest(msg=expected_error):
                test_lambda_event = copy.deepcopy(self.test_lambda_event)
                test_lambda_event["multiValueQueryStringParameters"]["-immunization.target"] = test_patient_id

                # When
                response = self.controller.search_immunizations(test_lambda_event)

                # Then
                self.assertEqual(response["statusCode"], 400)
                self.assertEqual(
                    json.loads(response["body"])["issue"][0]["diagnostics"],
                    expected_error,
                )
                self.service.search_immunizations.assert_not_called()

    def test_search_immunizations_returns_a_validation_error_when_optional_params_invalid(self):
        """it should return a 400 invalid error for multiple invalid optional parameter scenarios"""
        test_cases = [
            ("-date.to", ["2000-01-01,2000-10-10"], "Search parameter -date.to may have one value at most."),
            ("-date.to", ["hello-world"], "Search parameter -date.to must be in format: YYYY-MM-DD"),
            ("-date.from", ["2000-01-01,2000-10-10"], "Search parameter -date.from may have one value at most."),
            ("-date.from", ["hello-world"], "Search parameter -date.from must be in format: YYYY-MM-DD"),
            (
                "_include",
                ["not-permitted-for-inclusion"],
                "Search parameter _include may only be 'Immunization:patient' if provided.",
            ),
        ]

        for key_with_error, test_data, expected_error in test_cases:
            with self.subTest(msg=expected_error):
                test_lambda_event = copy.deepcopy(self.test_lambda_event)
                test_lambda_event["multiValueQueryStringParameters"][key_with_error] = test_data

                # When
                response = self.controller.search_immunizations(test_lambda_event)

                # Then
                self.assertEqual(response["statusCode"], 400)
                self.assertEqual(
                    json.loads(response["body"])["issue"][0]["diagnostics"],
                    expected_error,
                )
                self.service.search_immunizations.assert_not_called()

    @patch("controller.fhir_controller.MAX_RESPONSE_SIZE_BYTES", 5)
    def test_search_immunizations_raises_error_if_too_many_results_found(self):
        """it should return an error if there are too many results in the response for Lambda to handle. In reality,
        highly unlikely. If a concern, pagination should be implemented."""
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "something"}))],
            link=[BundleLink.construct(relation="self", url="patient-search-url")],
            type="searchset",
            total=1,
        )

        # When
        response = self.controller.search_immunizations(self.test_lambda_event)

        # Then
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value,
            {"COVID"},
            "test",
            datetime.date(2000, 1, 1),
            datetime.date(2024, 1, 1),
            "Immunization:patient",
        )
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(
            json.loads(response["body"])["issue"][0]["diagnostics"],
            "Search returned too many results. Please narrow down the search",
        )
