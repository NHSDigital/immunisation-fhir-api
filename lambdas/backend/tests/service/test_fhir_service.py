import datetime
import json
import os
import unittest
import uuid
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, create_autospec, patch

from fhir.resources.R4B.bundle import Bundle as FhirBundle
from fhir.resources.R4B.bundle import BundleEntry
from fhir.resources.R4B.immunization import Immunization

from authorisation.api_operation_code import ApiOperationCode
from authorisation.authoriser import Authoriser
from common.models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    InconsistentIdentifierError,
    InconsistentResourceVersion,
    ResourceNotFoundError,
)
from common.models.fhir_immunization import ImmunizationValidator
from common.models.immunization_record_metadata import ImmunizationRecordMetadata
from models.errors import UnauthorizedVaxError
from repository.fhir_repository import ImmunizationRepository
from service.fhir_service import FhirService, get_service_url
from test_common.testing_utils.generic_utils import load_json_data
from test_common.testing_utils.immunization_utils import (
    VALID_NHS_NUMBER,
    create_covid_immunization,
    create_covid_immunization_dict,
    create_covid_immunization_dict_no_id,
)
from test_common.validator.testing_utils.csv_fhir_utils import parse_test_file

# Constants for use within the tests
NHS_NUMBER_USED_IN_SAMPLE_DATA = "9000000009"


class TestFhirServiceBase(unittest.TestCase):
    """Base class for all tests to set up common fixtures"""

    def setUp(self):
        super().setUp()
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("common.models.utils.validation_utils.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        super().tearDown()
        patch.stopall()


class TestServiceUrl(unittest.TestCase):
    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_service_url(self):
        """it should create service url"""
        env = "int"
        base_path = "immunisation-fhir-api/FHIR/R4"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://{env}.api.service.nhs.uk/{base_path}")
        # default should be internal-dev
        env = "it-does-not-exist"
        base_path = "immunisation-fhir-api/FHIR/R4"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://internal-dev.api.service.nhs.uk/{base_path}")
        # prod should not have a subdomain
        env = "prod"
        base_path = "immunisation-fhir-api/FHIR/R4"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://api.service.nhs.uk/{base_path}")
        # any other env should fall back to internal-dev (like pr-xx or per-user)
        env = "pr-42"
        base_path = "immunisation-fhir-api/FHIR/R4"
        url = get_service_url(env, base_path)
        self.assertEqual(url, f"https://internal-dev.api.service.nhs.uk/{base_path}")


class TestGetImmunization(TestFhirServiceBase):
    """Tests for FhirService.get_immunization_by_id"""

    def setUp(self):
        super().setUp()
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_immunization_by_id(self):
        """it should find an Immunization by id"""
        imms_id = "an-id"
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            create_covid_immunization(imms_id).dict(),
            ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False),
        )

        # When
        immunisation, version = self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test Supplier", ApiOperationCode.READ, {"COVID"})
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id)

        self.assertEqual(immunisation.id, imms_id)
        self.assertEqual(version, "1")

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = None, None

        # When
        with self.assertRaises(ResourceNotFoundError) as error:
            self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id)
        self.assertEqual(
            "Immunization resource does not exist. ID: non-existent-id",
            str(error.exception),
        )

    def test_get_immunization_by_id_patient_not_restricted(self):
        """
        Test that get_immunization_by_id returns a FHIR Immunization Resource which has been filtered for read
        when patient is not restricted
        """
        imms_id = "non_restricted_id"

        immunization_data = load_json_data("completed_covid_immunization_event.json")
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            immunization_data,
            ImmunizationRecordMetadata(resource_version=2, is_deleted=False, is_reinstated=False),
        )

        expected_imms = load_json_data("completed_covid_immunization_event_for_read.json")
        expected_output = Immunization.parse_obj(expected_imms)

        # When
        actual_output, version = self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test Supplier", ApiOperationCode.READ, {"COVID"})
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id)
        self.assertEqual(actual_output, expected_output)
        self.assertEqual(version, "2")

    def test_unauthorised_error_raised_when_user_lacks_permissions(self):
        """it should throw an exception when user lacks permissions"""
        imms_id = "an-id"
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = False
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            create_covid_immunization(imms_id).dict(),
            ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False),
        )

        with self.assertRaises(UnauthorizedVaxError):
            # When
            self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test Supplier", ApiOperationCode.READ, {"COVID"})
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id)


class TestGetImmunizationIdentifier(unittest.TestCase):
    """Tests for FhirService.get_immunization_by_id"""

    MOCK_SUPPLIER_NAME = "TestSupplier"

    def setUp(self):
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_get_immunization_by_identifier(self):
        """it should find an Immunization by id"""
        imms_id = "an-id#an-id"
        identifier = "test"
        element = "id,mEta,DDD"

        mock_resource = create_covid_immunization_dict(identifier)
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_by_identifier.return_value = (
            {
                "resource": mock_resource,
                "id": imms_id,
                "version": 1,
            },
            "covid",
        )

        # When
        service_resp = self.fhir_service.get_immunization_by_identifier(
            imms_id, self.MOCK_SUPPLIER_NAME, identifier, element
        )

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(imms_id)
        self.authoriser.authorise.assert_called_once_with(self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, {"covid"})
        self.assertEqual(service_resp["resourceType"], "Bundle")
        self.assertEqual(service_resp.get("type"), "searchset")
        self.assertIn("entry", service_resp)
        self.assertEqual(len(service_resp["entry"]), 1)
        self.assertIn("total", service_resp)
        self.assertEqual(service_resp["total"], 1)
        res = service_resp["entry"][0]["resource"]
        self.assertEqual(res["resourceType"], "Immunization")
        self.assertEqual(res["id"], imms_id)

    def test_get_immunization_by_identifier_raises_error_when_not_authorised(self):
        """it should find an Immunization by id"""
        imms = "an-id#an-id"
        identifier = "test"
        element = "id,mEta,DDD"
        self.authoriser.authorise.return_value = False
        self.imms_repo.get_immunization_by_identifier.return_value = (
            {
                "id": "foo",
                "version": 1,
            },
            "covid",
        )

        with self.assertRaises(UnauthorizedVaxError):
            # When
            self.fhir_service.get_immunization_by_identifier(imms, self.MOCK_SUPPLIER_NAME, identifier, element)

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(imms)
        self.authoriser.authorise.assert_called_once_with(self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, {"covid"})

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "none"
        identifier = "test"
        element = "id"
        self.imms_repo.get_immunization_by_identifier.return_value = None, None

        # When
        act_imms = self.fhir_service.get_immunization_by_identifier(
            imms_id, self.MOCK_SUPPLIER_NAME, identifier, element
        )

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(imms_id)

        self.assertEqual(act_imms["entry"], [])


class TestCreateImmunization(TestFhirServiceBase):
    """Tests for FhirService.create_immunization"""

    _MOCK_NEW_UUID = "88ca94d9-4618-4dc1-9e94-e701d3b2dd06"

    def setUp(self):
        super().setUp()

        # this one to mock the redis client in fhir_immunization.
        # note: not all the tests might be valid any more now that we're using the Validator;
        # anything in here which specifically tests the output of the Validator may fail, as it
        # used to test the output of the old PreValidators.
        self.mock_validator_redis = Mock()
        self.validator_redis_getter_patcher = patch("common.models.fhir_immunization.get_redis_client")
        self.mock_validator_redis_getter = self.validator_redis_getter_patcher.start()
        # test schema file
        validation_folder = Path(__file__).resolve().parent
        self.schemaFilePath = validation_folder / "test_schemas/test_schema.json"
        self.schemaFile = parse_test_file(self.schemaFilePath)
        self.mock_validator_redis.hget.return_value = self.schemaFile
        self.mock_validator_redis_getter.return_value = self.mock_validator_redis

        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = ImmunizationValidator()
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)

    def test_create_immunization(self):
        """it should create Immunization and validate it"""
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.check_immunization_identifier_exists.return_value = False
        self.imms_repo.create_immunization.return_value = self._MOCK_NEW_UUID

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_immunization_dict_no_id(nhs_number)

        # When
        created_id = self.fhir_service.create_immunization(req_imms, "Test")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.CREATE, {"COVID"})
        self.imms_repo.check_immunization_identifier_exists.assert_called_once_with(
            "https://supplierABC/identifiers/vacc", "ACME-vacc123456"
        )
        self.imms_repo.create_immunization.assert_called_once_with(Immunization.parse_obj(req_imms), "Test")

        #self.validator.validate.assert_called_once_with(req_imms)
        self.assertEqual(self._MOCK_NEW_UUID, created_id)

    def test_create_immunization_with_id_throws_error(self):
        """it should throw exception if id present in create Immunization"""
        imms = create_covid_immunization_dict("an-id", "9990548609")
        expected_msg = "id field must not be present for CREATE operation"

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.fhir_service.create_immunization(imms, "Test")

        # Then
        print(error.exception.message)
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    def test_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        self.imms_repo.check_immunization_identifier_exists.return_value = False
        imms = create_covid_immunization_dict_no_id("9990548609")
        imms["lotNumber"] = ""
        expected_msg = [
            {
                "code": 5,
                "message": "Value not empty failure",
                "row": 2,
                "field": "lotNumber",
                "details": "Value is empty, not as expected"
            }
        ]

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.fhir_service.create_immunization(imms, "Test")

        # Then
        print(error.exception.message)
        self.assertEqual(json.dumps(expected_msg), error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    def test_validation_failed_create_invalid_target_disease(self):
        """it should raise CustomValidationError for invalid target disease code on create"""
        self.mock_redis.hget.return_value = None
        self.mock_redis_getter.return_value = self.mock_redis
        self.imms_repo.check_immunization_identifier_exists.return_value = False
        valid_imms = create_covid_immunization_dict_no_id(VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        bad_target_disease_msg = (
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')]"
            + ".code - ['bad-code'] is not a valid combination of disease codes for this service"
        )

        with self.assertRaises(ValueError) as error:
            self.fhir_service.create_immunization(bad_target_disease_imms, "Test")

        actual_errors = str(error.exception).split("; ")
        self.assertEqual(bad_target_disease_msg, actual_errors[0])
        self.imms_repo.create_immunization.assert_not_called()

    # NB this is picked up in the validator now i.e. in pre-validation.
    def test_validation_failed_create_missing_patient_name(self):
        """it should raise CustomValidationError for missing patient name on create"""
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.imms_repo.check_immunization_identifier_exists.return_value = False
        valid_imms = create_covid_immunization_dict_no_id(VALID_NHS_NUMBER)

        bad_patient_name_imms = deepcopy(valid_imms)
        bad_patient_name_imms["contained"][1]["name"][0]["given"] = None

        bad_patient_name_msg = [
            {
                "code": 5,
                "message": "Value not empty failure",
                "row": 2,
                "field": "contained|#:Patient|name|#:official|given|0",
                "details": "Value is empty, not as expected"
            }
        ]
        with self.assertRaises(CustomValidationError) as error:
            self.fhir_service.create_immunization(bad_patient_name_imms, "Test")

        # Then
        print(error.exception.message)
        self.assertEqual(json.dumps(bad_patient_name_msg), error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    # NOTE: this test will fail for now. The stub validator isn't checking NHS numbers. It will.
    '''
    def test_patient_error(self):
        """it should throw error when patient ID is invalid"""
        self.imms_repo.check_immunization_identifier_exists.return_value = False
        invalid_nhs_number = "9434765911"  # check digit 1 doesn't match result (9)
        imms = create_covid_immunization_dict_no_id(invalid_nhs_number)
        expected_msg = {
            "code": 12,
            "message": "Key lookup failure",
            "row": 2,
            "field": "performer|#:Organization|actor|identifier|value",
            "details": "Value was not found in Key List, Expected- B0C4P Found- nothing"
        }
        with self.assertRaises(CustomValidationError) as error:
            # When
            self.fhir_service.create_immunization(imms, "Test")

        # Then
        self.assertIn(json.dumps(expected_msg), error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()
    '''
    
    def test_unauthorised_error_raised_when_user_lacks_permissions(self):
        """it should raise error when user lacks permissions"""
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = False
        self.imms_repo.create_immunization.return_value = create_covid_immunization_dict_no_id()

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_immunization_dict_no_id(nhs_number)

        with self.assertRaises(UnauthorizedVaxError):
            # When
            self.fhir_service.create_immunization(req_imms, "Test")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.CREATE, {"COVID"})
        # self.validator.validate.assert_called_once_with(req_imms)
        self.imms_repo.create_immunization.assert_not_called()

    def test_raises_duplicate_error_if_identifier_already_exits(self):
        """it should raise a duplicate error if the immunisation identifier (system + local ID) already exists"""
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.check_immunization_identifier_exists.return_value = True

        nhs_number = VALID_NHS_NUMBER
        req_imms = create_covid_immunization_dict_no_id(nhs_number)

        # When
        with self.assertRaises(IdentifierDuplicationError) as error:
            self.fhir_service.create_immunization(req_imms, "Test")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.CREATE, {"COVID"})
        self.imms_repo.check_immunization_identifier_exists.assert_called_once_with(
            "https://supplierABC/identifiers/vacc", "ACME-vacc123456"
        )
        self.imms_repo.create_immunization.assert_not_called()
        # self.validator.validate.assert_called_once_with(req_imms)
        self.assertEqual(
            "The provided identifier: https://supplierABC/identifiers/vacc#ACME-vacc123456 is duplicated",
            str(error.exception),
        )


class TestUpdateImmunization(TestFhirServiceBase):
    """Tests for FhirService.update_immunization"""

    def setUp(self):
        super().setUp()
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser)
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis

        self.mock_validator_redis = Mock()
        self.validator_redis_getter_patcher = patch("common.models.fhir_immunization.get_redis_client")
        self.mock_validator_redis_getter = self.validator_redis_getter_patcher.start()
        # test schema file
        validation_folder = Path(__file__).resolve().parent
        self.schemaFilePath = validation_folder / "test_schemas/test_schema.json"
        self.schemaFile = parse_test_file(self.schemaFilePath)
        self.mock_validator_redis.hget.return_value = self.schemaFile
        self.mock_validator_redis_getter.return_value = self.mock_validator_redis

    def test_update_immunization(self):
        """it should update Immunization and validate NHS number"""
        imms_id = "an-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")
        existing_resource_meta = ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False)

        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            original_immunisation,
            existing_resource_meta,
        )
        self.imms_repo.update_immunization.return_value = 2
        self.authoriser.authorise.return_value = True

        # When
        updated_version = self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 1)

        # Then
        self.assertEqual(updated_version, 2)
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id, include_deleted=True)
        self.imms_repo.update_immunization.assert_called_once_with(
            imms_id, updated_immunisation, existing_resource_meta, "Test"
        )
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.UPDATE, {"COVID"})

    def test_update_immunization_raises_validation_exception_when_nhs_number_invalid(self):
        """it should raise a CustomValidationError when the patient's NHS number in the payload is invalid"""
        imms_id = "an-id"
        invalid_imms = create_covid_immunization_dict(imms_id, "12345678")

        # When
        with self.assertRaises(CustomValidationError) as error:
            self.fhir_service.update_immunization(imms_id, invalid_imms, "Test", 1)

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_not_called()
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(
            error.exception.message,
            "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value must be 10 characters",
        )

    def test_update_immunization_raises_not_found_error_when_no_existing_immunisation(self):
        """it should raise a ResourceNotFoundError exception if no immunisation exists for the given ID"""
        imms_id = "non-existent-id-123"
        requested_imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)

        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (None, None)

        # When
        with self.assertRaises(ResourceNotFoundError) as error:
            self.fhir_service.update_immunization(imms_id, requested_imms, "Test", 1)

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id, include_deleted=True)
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(str(error.exception), "Immunization resource does not exist. ID: non-existent-id-123")

    def test_update_immunization_raises_unauthorized_exception_when_user_lacks_permissions(self):
        """it should raise an UnauthorizedVaxError exception if the user does not have permissions for the Update
        interaction with the target vaccination"""
        imms_id = "test-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")

        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            original_immunisation,
            ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=True),
        )
        self.authoriser.authorise.return_value = False

        # When
        with self.assertRaises(UnauthorizedVaxError):
            self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 1)

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id, include_deleted=True)
        self.imms_repo.update_immunization.assert_not_called()

    def test_update_immunization_raises_invalid_error_if_identifiers_do_not_match(self):
        """it should raise an InconsistentIdentifierError if the local identifier in the update does not match that in
        the stored resource"""
        imms_id = "test-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        original_immunisation["identifier"][0]["system"] = "legacyUri.com"
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")

        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            original_immunisation,
            ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False),
        )
        self.authoriser.authorise.return_value = True

        # When
        with self.assertRaises(InconsistentIdentifierError) as error:
            self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 1)

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id, include_deleted=True)
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(
            str(error.exception), "Validation errors: identifier[0].system doesn't match with the stored content"
        )

    def test_update_immunization_raises_invalid_error_if_resource_version_does_not_match(self):
        """it should raise an InconsistentResourceVersion if the resource version provided in the request does not match
        the current version of the stored resource"""
        imms_id = "test-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")

        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            original_immunisation,
            ImmunizationRecordMetadata(resource_version=4, is_deleted=False, is_reinstated=False),
        )
        self.authoriser.authorise.return_value = True

        # When
        with self.assertRaises(InconsistentResourceVersion) as error:
            self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 2)

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(imms_id, include_deleted=True)
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(
            str(error.exception),
            "Validation errors: The requested immunization resource test-id has changed since the last retrieve.",
        )


class TestDeleteImmunization(TestFhirServiceBase):
    """Tests for FhirService.delete_immunization"""

    TEST_IMMUNISATION_ID = "an-id"

    def setUp(self):
        super().setUp()
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)

    def test_delete_immunization(self):
        """it should delete Immunization record"""
        imms = json.loads(create_covid_immunization(self.TEST_IMMUNISATION_ID).json())
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            imms,
            ImmunizationRecordMetadata(resource_version=1, is_deleted=False, is_reinstated=False),
        )
        self.imms_repo.delete_immunization.return_value = None

        # When
        self.fhir_service.delete_immunization(self.TEST_IMMUNISATION_ID, "Test")

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(self.TEST_IMMUNISATION_ID)
        self.imms_repo.delete_immunization.assert_called_once_with(self.TEST_IMMUNISATION_ID, "Test")
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.DELETE, {"COVID"})

    def test_delete_immunization_throws_not_found_exception_if_does_not_exist(self):
        """it should raise a ResourceNotFound exception if the immunisation does not exist"""
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (None, None)

        # When
        with self.assertRaises(ResourceNotFoundError):
            self.fhir_service.delete_immunization(self.TEST_IMMUNISATION_ID, "Test")

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(self.TEST_IMMUNISATION_ID)
        self.imms_repo.delete_immunization.assert_not_called()

    def test_delete_immunization_throws_authorisation_exception_if_does_not_have_required_permissions(
        self,
    ):
        """it should raise an UnauthorizedVaxError when the client does not have permissions for the given vacc type"""
        imms = json.loads(create_covid_immunization(self.TEST_IMMUNISATION_ID).json())
        self.mock_redis.hget.return_value = "FLU"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = False
        self.imms_repo.get_immunization_and_resource_meta_by_id.return_value = (
            imms,
            ImmunizationRecordMetadata(resource_version=2, is_deleted=False, is_reinstated=False),
        )

        # When
        with self.assertRaises(UnauthorizedVaxError):
            self.fhir_service.delete_immunization(self.TEST_IMMUNISATION_ID, "Test")

        # Then
        self.imms_repo.get_immunization_and_resource_meta_by_id.assert_called_once_with(self.TEST_IMMUNISATION_ID)
        self.imms_repo.delete_immunization.assert_not_called()
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.DELETE, {"FLU"})


class TestSearchImmunizations(unittest.TestCase):
    """Tests for FhirService.search_immunizations"""

    MOCK_SUPPLIER_SYSTEM_NAME = "Test"

    def setUp(self):
        os.environ["IMMUNIZATION_ENV"] = "internal-dev"
        os.environ["IMMUNIZATION_BASE_PATH"] = "immunisation-fhir-api/FHIR/R4"
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)
        self.nhs_search_param = "patient.identifier"
        self.vaccine_type_search_param = "-immunization.target"
        self.sample_patient_resource = load_json_data("bundle_patient_resource.json")

    def test_vaccine_type_search(self):
        """It should search for the correct vaccine type"""
        nhs_number = VALID_NHS_NUMBER
        vaccine_type = "COVID"
        params = f"{self.nhs_search_param}={nhs_number}&{self.vaccine_type_search_param}={vaccine_type}"

        self.authoriser.filter_permitted_vacc_types.return_value = {vaccine_type}
        self.imms_repo.find_immunizations.return_value = []

        # When
        _ = self.fhir_service.search_immunizations(nhs_number, [vaccine_type], params, self.MOCK_SUPPLIER_SYSTEM_NAME)

        # Then
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {vaccine_type}
        )
        self.imms_repo.find_immunizations.assert_called_once_with(nhs_number, {vaccine_type})

    def test_make_fhir_bundle_from_search_result(self):
        """It should return a FHIR Bundle resource"""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        params = f"{self.nhs_search_param}={nhs_number}&{self.vaccine_type_search_param}={vaccine_types}"
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)
        # When
        result, contains_unauthorised_vaccs = self.fhir_service.search_immunizations(
            nhs_number, vaccine_types, params, self.MOCK_SUPPLIER_SYSTEM_NAME
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]
        # Then
        self.assertIsInstance(result, FhirBundle)
        self.assertEqual(result.type, "searchset")
        self.assertEqual(len(imms_ids), len(searched_imms))
        self.assertFalse(contains_unauthorised_vaccs)
        # Assert each entry in the bundle
        for i, entry in enumerate(searched_imms):
            self.assertIsInstance(entry, BundleEntry)
            self.assertEqual(entry.resource.resource_type, "Immunization")
            self.assertEqual(entry.resource.id, imms_ids[i])
        # Assert self link
        self.assertEqual(len(result.link), 1)
        self.assertEqual(result.link[0].relation, "self")

    def test_date_from_is_used_to_filter(self):
        """It should return only Immunizations after date_from"""
        # Arrange
        imms = [
            ("imms-1", "2021-02-07T13:28:17.271+00:00"),
            ("imms-2", "2021-02-08T13:28:17.271+00:00"),
        ]
        imms_list = [
            create_covid_immunization_dict(imms_id, occurrence_date_time=occcurrence_date_time)
            for (imms_id, occcurrence_date_time) in imms
        ]
        imms_ids = [imms[0] for imms in imms]
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # CASE: Day before.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_from=datetime.date(2021, 2, 6),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(2, len(searched_imms))
        for i, entry in enumerate(searched_imms):
            self.assertEqual(imms_ids[i], entry.resource.id)

        # CASE:Day of first, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_from=datetime.date(2021, 2, 7),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(2, len(searched_imms))
        for i, entry in enumerate(searched_imms):
            self.assertEqual(imms_ids[i], entry.resource.id)

        # CASE: Day of second, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_from=datetime.date(2021, 2, 8),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(1, len(searched_imms))
        self.assertEqual(imms_ids[1], searched_imms[0].resource.id)

        # CASE: Day after.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_from=datetime.date(2021, 2, 9),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(0, len(searched_imms))

    def test_date_from_is_optional(self):
        """It should return everything when no date_from is specified"""
        # Arrange
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # CASE: Without date_from
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "", self.MOCK_SUPPLIER_SYSTEM_NAME)
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE: With date_from
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_from=datetime.date(2021, 3, 6),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

    def test_date_to_is_used_to_filter(self):
        """It should return only Immunizations before date_to"""
        # Arrange
        imms = [
            ("imms-1", "2021-02-07T13:28:17.271+00:00"),
            ("imms-2", "2021-02-08T13:28:17.271+00:00"),
        ]
        imms_list = [
            create_covid_immunization_dict(imms_id, occurrence_date_time=occcurrence_date_time)
            for (imms_id, occcurrence_date_time) in imms
        ]
        imms_ids = [imms[0] for imms in imms]
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # CASE: Day after.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_to=datetime.date(2021, 2, 9),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 2)
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE: Day of second, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_to=datetime.date(2021, 2, 8),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 2)
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE: Day of first, inclusive search.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_to=datetime.date(2021, 2, 7),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 1)
        self.assertEqual(searched_imms[0].resource.id, imms_ids[0])

        # CASE: Day before.
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_to=datetime.date(2021, 2, 6),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        self.assertEqual(len(searched_imms), 0)

    def test_date_to_is_optional(self):
        """It should return everything when no date_to is specified"""
        # Arrange
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # CASE 1: Without date_to argument
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "", self.MOCK_SUPPLIER_SYSTEM_NAME)
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

        # CASE 2: With date_to argument
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            nhs_number,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            date_to=datetime.date(2021, 3, 8),
        )
        searched_imms = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(searched_imms):
            self.assertEqual(entry.resource.id, imms_ids[i])

    def test_immunization_resources_are_filtered_for_search(self):
        """
        Test that each immunization resource returned is filtered to include only the appropriate fields for a search
        response when the patient is Unrestricted
        """
        self.maxDiff = None
        
        # Arrange
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [
            create_covid_immunization_dict(
                imms_id,
                NHS_NUMBER_USED_IN_SAMPLE_DATA,
                occurrence_date_time="2021-02-07T13:28:17+00:00",
            )
            for imms_id in imms_ids
        ]

        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)
        self.imms_repo.find_immunizations.return_value = deepcopy(imms_list)

        # When
        result, _ = self.fhir_service.search_immunizations(
            NHS_NUMBER_USED_IN_SAMPLE_DATA,
            vaccine_types,
            "",
            self.MOCK_SUPPLIER_SYSTEM_NAME,
        )
        searched_imms = [
            json.loads(entry.json(), parse_float=Decimal)
            for entry in result.entry
            if entry.resource.resource_type == "Immunization"
        ]
        searched_patient = [
            json.loads(entry.json()) for entry in result.entry if entry.resource.resource_type == "Patient"
        ][0]

        # Then
        expected_output_resource = load_json_data(
            "completed_covid_immunization_event_filtered_for_search_using_bundle_patient_resource.json"
        )
        expected_output_resource["patient"]["reference"] = searched_patient["fullUrl"]

        for i, entry in enumerate(searched_imms):
            # Check that entry has correct resource id
            self.assertEqual(entry["resource"]["id"], imms_ids[i])

            # Check that output is as expected (filtered, with id added)
            expected_output_resource["id"] = imms_ids[i]
            self.assertEqual(entry["resource"], expected_output_resource)

    def test_matches_contain_fullUrl(self):
        """All matches must have a fullUrl consisting of their id.
        See http://hl7.org/fhir/R4B/bundle-definitions.html#Bundle.entry.fullUrl.
        Tested because fhir.resources validation doesn't check this as mandatory."""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # When
        result, _ = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "", self.MOCK_SUPPLIER_SYSTEM_NAME)
        entries = [entry for entry in result.entry if entry.resource.resource_type == "Immunization"]

        # Then
        for i, entry in enumerate(entries):
            self.assertEqual(
                entry.fullUrl,
                f"https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization/{imms_ids[i]}",
            )

    def test_patient_contains_fullUrl(self):
        """Patient must have a fullUrl consisting of its id.
        See http://hl7.org/fhir/R4B/bundle-definitions.html#Bundle.entry.fullUrl.
        Tested because fhir.resources validation doesn't check this as mandatory."""
        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        nhs_number = NHS_NUMBER_USED_IN_SAMPLE_DATA
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # When
        result, _ = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "", self.MOCK_SUPPLIER_SYSTEM_NAME)

        # Then
        patient_entry = next(
            (entry for entry in result.entry if entry.resource.resource_type == "Patient"),
            None,
        )
        patient_full_url = patient_entry.fullUrl
        self.assertTrue(patient_full_url.startswith("urn:uuid:"))

        # Check that final part of fullUrl is a uuid
        patient_full_url_uuid = patient_full_url.split(":")[2]
        self.assertTrue(uuid.UUID(patient_full_url_uuid))

    def test_patient_included(self):
        """Patient is included in the results."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # When
        result, _ = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "", self.MOCK_SUPPLIER_SYSTEM_NAME)

        # Then
        patient_entry = next((entry for entry in result.entry if entry.resource.resource_type == "Patient"))
        self.assertIsNotNone(patient_entry)

    def test_patient_is_stripped(self):
        """The included Patient is a subset of the data."""

        imms_ids = ["imms-1", "imms-2"]
        imms_list = [create_covid_immunization_dict(imms_id) for imms_id in imms_ids]
        self.imms_repo.find_immunizations.return_value = imms_list
        nhs_number = VALID_NHS_NUMBER
        vaccine_types = ["COVID"]
        self.authoriser.filter_permitted_vacc_types.return_value = set(vaccine_types)

        # When
        result, _ = self.fhir_service.search_immunizations(nhs_number, vaccine_types, "", self.MOCK_SUPPLIER_SYSTEM_NAME)

        # Then
        patient_entry = next((entry for entry in result.entry if entry.resource.resource_type == "Patient"))
        patient_entry_resource = patient_entry.resource
        fields_to_keep = ["id", "resource_type", "identifier"]
        # self.assertListEqual(sorted(vars(patient_entry.resource).keys()), sorted(fields_to_keep))
        # self.assertGreater(len(patient), len(fields_to_keep))
        for field in fields_to_keep:
            self.assertTrue(hasattr(patient_entry_resource, field), f"{field} in Patient")
            self.assertIsNotNone(getattr(patient_entry_resource, field))

        for k, v in vars(patient_entry_resource).items():
            if k not in fields_to_keep:
                self.assertIsNone(v)

    def test_search_raises_unauthorised_error_if_no_permissions(self):
        """It should raise an UnauthorisedVaxError if the supplier does not have permissions for ANY of the requested
        vaccination types"""
        vaccine_type = "COVID"
        params = f"{self.nhs_search_param}={VALID_NHS_NUMBER}&{self.vaccine_type_search_param}={vaccine_type}"

        self.authoriser.filter_permitted_vacc_types.return_value = {}

        # When
        with self.assertRaises(UnauthorizedVaxError):
            self.fhir_service.search_immunizations(
                VALID_NHS_NUMBER, [vaccine_type], params, self.MOCK_SUPPLIER_SYSTEM_NAME
            )

        # Then
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {vaccine_type}
        )
        self.imms_repo.find_immunizations.assert_not_called()

    def test_search_returns_successfully_but_flags_if_supplier_requests_vacc_types_without_perms(
        self,
    ):
        """It should return a boolean indicating if the supplier has requested one or more vaccination types which
        they do not have permission to search. This is a more permissive model and ensures that results are still
        returned for the vacc types that they can handle"""
        vaccine_types = ["COVID", "FLU"]
        params = f"{self.nhs_search_param}={VALID_NHS_NUMBER}&{self.vaccine_type_search_param}={vaccine_types}"

        # Supplier only has permission for Covid
        self.authoriser.filter_permitted_vacc_types.return_value = {"COVID"}

        # When
        _, request_has_unauthorised_vacc_types = self.fhir_service.search_immunizations(
            VALID_NHS_NUMBER, vaccine_types, params, self.MOCK_SUPPLIER_SYSTEM_NAME
        )

        # Then
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, set(vaccine_types)
        )
        # Only calls the repository for vacc types it is authorised for
        self.imms_repo.find_immunizations.assert_called_once_with(VALID_NHS_NUMBER, {"COVID"})
        self.assertTrue(request_has_unauthorised_vacc_types)
