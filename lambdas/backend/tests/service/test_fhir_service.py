import datetime
import json
import os
import unittest
from copy import deepcopy
from unittest.mock import Mock, create_autospec, patch

from fhir.resources.R4B.bundle import BundleLink
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.immunization import Immunization

from authorisation.api_operation_code import ApiOperationCode
from authorisation.authoriser import Authoriser
from common.models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    InconsistentIdentifierError,
    InconsistentResourceVersionError,
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
from test_common.testing_utils.values_for_tests import ValidValues

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
        immunisation_resource = create_covid_immunization(imms_id).dict()
        identifier = Identifier(
            system=immunisation_resource["identifier"][0]["system"],
            value=immunisation_resource["identifier"][0]["value"],
        )
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            immunisation_resource,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=False),
        )

        # When
        immunisation, version = self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test Supplier", ApiOperationCode.READ, {"COVID"})
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(imms_id)

        self.assertEqual(immunisation.id, imms_id)
        self.assertEqual(version, "1")

    def test_immunization_not_found(self):
        """it should return None if Immunization doesn't exist"""
        imms_id = "non-existent-id"
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = None, None

        # When
        with self.assertRaises(ResourceNotFoundError) as error:
            self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(imms_id)
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
        identifier = Identifier(
            system=immunization_data["identifier"][0]["system"], value=immunization_data["identifier"][0]["value"]
        )
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis

        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            immunization_data,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=2, is_deleted=False, is_reinstated=False),
        )

        expected_imms = load_json_data("completed_covid_immunization_event_for_read.json")
        expected_output = Immunization.parse_obj(expected_imms)

        # When
        actual_output, version = self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test Supplier", ApiOperationCode.READ, {"COVID"})
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(imms_id)
        self.assertEqual(actual_output, expected_output)
        self.assertEqual(version, "2")

    def test_unauthorised_error_raised_when_user_lacks_permissions(self):
        """it should throw an exception when user lacks permissions"""
        imms_id = "an-id"
        immunisation_resource = create_covid_immunization(imms_id).dict()
        identifier = Identifier(
            system=immunisation_resource["identifier"][0]["system"],
            value=immunisation_resource["identifier"][0]["value"],
        )
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = False
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            immunisation_resource,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=False),
        )

        with self.assertRaises(UnauthorizedVaxError):
            # When
            self.fhir_service.get_immunization_and_version_by_id(imms_id, "Test Supplier")

        # Then
        self.authoriser.authorise.assert_called_once_with("Test Supplier", ApiOperationCode.READ, {"COVID"})
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(imms_id)


class TestGetImmunizationByIdentifier(TestFhirServiceBase):
    """Tests for FhirService.get_immunization_by_id"""

    MOCK_SUPPLIER_NAME = "TestSupplier"
    test_identifier = Identifier.construct(system="some-system", value="some-value")
    mock_resource_meta = ImmunizationRecordMetadata(
        test_identifier, resource_version=1, is_deleted=False, is_reinstated=False
    )

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

    def test_get_immunization_by_identifier(self):
        """it should find an Immunization by identifier"""
        mock_resource = create_covid_immunization_dict("1234-some-id")
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_by_identifier.return_value = mock_resource, self.mock_resource_meta

        # When
        result = self.fhir_service.get_immunization_by_identifier(self.test_identifier, self.MOCK_SUPPLIER_NAME, None)

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(self.test_identifier)
        self.authoriser.authorise.assert_called_once_with(self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, {"COVID"})

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 1)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?identifier=some-"
                "system|some-value",
            ),
        )

        # Search function adds meta to the resource
        mock_resource["meta"] = {"versionId": "1"}
        self.assertEqual(result.entry[0].resource, Immunization.parse_obj(mock_resource))

    def test_get_immunization_by_identifier_raises_error_when_not_authorised(self):
        """it should return an unauthorized error when the client does not have authorization for the vacc type"""
        mock_resource = create_covid_immunization_dict("1234-some-id")
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = False
        self.imms_repo.get_immunization_by_identifier.return_value = mock_resource, self.mock_resource_meta

        with self.assertRaises(UnauthorizedVaxError):
            # When
            self.fhir_service.get_immunization_by_identifier(self.test_identifier, self.MOCK_SUPPLIER_NAME, None)

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(self.test_identifier)
        self.authoriser.authorise.assert_called_once_with(self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, {"COVID"})

    def test_get_immunization_by_identifier_returns_empty_search_when_not_found(self):
        """it should return an empty search bundle when the resource is not found"""
        self.imms_repo.get_immunization_by_identifier.return_value = None, None

        # When
        result = self.fhir_service.get_immunization_by_identifier(self.test_identifier, self.MOCK_SUPPLIER_NAME, None)

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(self.test_identifier)

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 0)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?identifier=some-"
                "system|some-value",
            ),
        )
        self.assertEqual(result.entry, [])

    def test_get_immunization_by_identifier_when_elements_parameter_provided(self):
        """it should return a subset of the resource when the _elements parameter is provided"""
        mock_resource = create_covid_immunization_dict("1234-some-id")
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_by_identifier.return_value = mock_resource, self.mock_resource_meta

        # When
        result = self.fhir_service.get_immunization_by_identifier(
            self.test_identifier, self.MOCK_SUPPLIER_NAME, {"id", "meta"}
        )

        # Then
        self.imms_repo.get_immunization_by_identifier.assert_called_once_with(self.test_identifier)
        self.authoriser.authorise.assert_called_once_with(self.MOCK_SUPPLIER_NAME, ApiOperationCode.SEARCH, {"COVID"})

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 1)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?identifier=some-"
                "system|some-value&_elements=id,meta",
            ),
        )
        self.assertEqual(
            result.entry[0].resource,
            Immunization.construct(**{"resourceType": "Immunization", "id": "1234-some-id", "meta": {"versionId": "1"}}),
        )


class TestCreateImmunization(TestFhirServiceBase):
    """Tests for FhirService.create_immunization"""

    _MOCK_NEW_UUID = "88ca94d9-4618-4dc1-9e94-e701d3b2dd06"

    def setUp(self):
        super().setUp()
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)
        self.pre_validate_fhir_service = FhirService(
            self.imms_repo,
            self.authoriser,
            ImmunizationValidator(add_post_validators=False),
        )

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

        self.validator.validate.assert_called_once_with(req_imms)
        self.assertEqual(self._MOCK_NEW_UUID, created_id)

    def test_create_immunization_with_id_throws_error(self):
        """it should throw exception if id present in create Immunization"""
        imms = create_covid_immunization_dict("an-id", "9990548609")
        expected_msg = "id field must not be present for CREATE operation"

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(imms, "Test")

        # Then
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    def test_pre_validation_failed(self):
        """it should throw exception if Immunization is not valid"""
        imms = create_covid_immunization_dict_no_id("9990548609")
        imms["lotNumber"] = 1234
        expected_msg = "lotNumber must be a string"

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(imms, "Test")

        # Then
        self.assertTrue(expected_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    def test_post_validation_failed_create_invalid_target_disease(self):
        """it should raise CustomValidationError for invalid target disease code on create"""
        self.mock_redis.hget.return_value = None
        self.mock_redis_getter.return_value = self.mock_redis
        valid_imms = create_covid_immunization_dict_no_id(VALID_NHS_NUMBER)

        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        bad_target_disease_msg = (
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')]"
            + ".code - ['bad-code'] is not a valid combination of disease codes for this service"
        )

        fhir_service = FhirService(self.imms_repo)

        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_target_disease_imms, "Test")

        self.assertEqual(bad_target_disease_msg, error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    def test_post_validation_failed_create_missing_patient_name(self):
        """it should raise CustomValidationError for missing patient name on create"""
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        valid_imms = create_covid_immunization_dict_no_id(VALID_NHS_NUMBER)

        bad_patient_name_imms = deepcopy(valid_imms)
        del bad_patient_name_imms["contained"][1]["name"][0]["given"]
        bad_patient_name_msg = "contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"

        fhir_service = FhirService(self.imms_repo)

        with self.assertRaises(CustomValidationError) as error:
            fhir_service.create_immunization(bad_patient_name_imms, "Test")

        self.assertTrue(bad_patient_name_msg in error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

    def test_patient_error(self):
        """it should throw error when patient ID is invalid"""
        invalid_nhs_number = "9434765911"  # check digit 1 doesn't match result (9)
        imms = create_covid_immunization_dict_no_id(invalid_nhs_number)
        expected_msg = (
            "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value is not a valid NHS number"
        )

        with self.assertRaises(CustomValidationError) as error:
            # When
            self.pre_validate_fhir_service.create_immunization(imms, "Test")

        # Then
        self.assertEqual(expected_msg, error.exception.message)
        self.imms_repo.create_immunization.assert_not_called()

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
        self.validator.validate.assert_called_once_with(req_imms)
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
        self.validator.validate.assert_called_once_with(req_imms)
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

    def test_update_immunization(self):
        """it should update Immunization and validate NHS number"""
        imms_id = "an-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        identifier = Identifier(
            system=original_immunisation["identifier"][0]["system"],
            value=original_immunisation["identifier"][0]["value"],
        )
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")
        existing_resource_meta = ImmunizationRecordMetadata(
            identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=False
        )

        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            original_immunisation,
            existing_resource_meta,
        )
        self.imms_repo.update_immunization.return_value = 2
        self.authoriser.authorise.return_value = True

        # When
        updated_version = self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 1)

        # Then
        self.assertEqual(updated_version, 2)
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(
            imms_id, include_deleted=True
        )
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
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_not_called()
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(
            error.exception.message,
            "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value must be 10 characters",
        )

    def test_update_immunization_raises_not_found_error_when_no_existing_immunisation(self):
        """it should raise a ResourceNotFoundError exception if no immunisation exists for the given ID"""
        imms_id = "non-existent-id-123"
        requested_imms = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)

        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (None, None)

        # When
        with self.assertRaises(ResourceNotFoundError) as error:
            self.fhir_service.update_immunization(imms_id, requested_imms, "Test", 1)

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(
            imms_id, include_deleted=True
        )
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(str(error.exception), "Immunization resource does not exist. ID: non-existent-id-123")

    def test_update_immunization_raises_unauthorized_exception_when_user_lacks_permissions(self):
        """it should raise an UnauthorizedVaxError exception if the user does not have permissions for the Update
        interaction with the target vaccination"""
        imms_id = "test-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        identifier = Identifier(
            system=original_immunisation["identifier"][0]["system"],
            value=original_immunisation["identifier"][0]["value"],
        )
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")

        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            original_immunisation,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=True),
        )
        self.authoriser.authorise.return_value = False

        # When
        with self.assertRaises(UnauthorizedVaxError):
            self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 1)

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(
            imms_id, include_deleted=True
        )
        self.imms_repo.update_immunization.assert_not_called()

    def test_update_immunization_raises_invalid_error_if_identifiers_do_not_match(self):
        """it should raise an InconsistentIdentifierError if the local identifier in the update does not match the
        IdentifierPK stored in the database"""
        imms_id = "test-id"
        immunisation_resource = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        identifier = Identifier(
            system="legacyUri.com",
            value=immunisation_resource["identifier"][0]["value"],
        )

        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            immunisation_resource,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=False),
        )
        self.authoriser.authorise.return_value = True

        # When
        with self.assertRaises(InconsistentIdentifierError) as error:
            self.fhir_service.update_immunization(imms_id, immunisation_resource, "Test", 1)

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(
            imms_id, include_deleted=True
        )
        self.imms_repo.update_immunization.assert_not_called()
        self.assertEqual(
            str(error.exception), "Validation errors: identifier[0].system doesn't match with the stored content"
        )

    def test_update_immunization_raises_invalid_error_if_resource_version_does_not_match(self):
        """it should raise an InconsistentResourceVersion if the resource version provided in the request does not match
        the current version of the stored resource"""
        imms_id = "test-id"
        original_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER)
        identifier = Identifier(
            system=original_immunisation["identifier"][0]["system"],
            value=original_immunisation["identifier"][0]["value"],
        )
        updated_immunisation = create_covid_immunization_dict(imms_id, VALID_NHS_NUMBER, "2021-02-07T13:28:00+00:00")

        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            original_immunisation,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=4, is_deleted=False, is_reinstated=False),
        )
        self.authoriser.authorise.return_value = True

        # When
        with self.assertRaises(InconsistentResourceVersionError) as error:
            self.fhir_service.update_immunization(imms_id, updated_immunisation, "Test", 2)

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(
            imms_id, include_deleted=True
        )
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
        identifier = Identifier(system=imms["identifier"][0]["system"], value=imms["identifier"][0]["value"])
        self.mock_redis.hget.return_value = "COVID"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = True
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            imms,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=False),
        )
        self.imms_repo.delete_immunization.return_value = None

        # When
        self.fhir_service.delete_immunization(self.TEST_IMMUNISATION_ID, "Test")

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(self.TEST_IMMUNISATION_ID)
        self.imms_repo.delete_immunization.assert_called_once_with(self.TEST_IMMUNISATION_ID, "Test")
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.DELETE, {"COVID"})

    def test_delete_immunization_throws_not_found_exception_if_does_not_exist(self):
        """it should raise a ResourceNotFound exception if the immunisation does not exist"""
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (None, None)

        # When
        with self.assertRaises(ResourceNotFoundError):
            self.fhir_service.delete_immunization(self.TEST_IMMUNISATION_ID, "Test")

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(self.TEST_IMMUNISATION_ID)
        self.imms_repo.delete_immunization.assert_not_called()

    def test_delete_immunization_throws_authorisation_exception_if_does_not_have_required_permissions(
        self,
    ):
        """it should raise an UnauthorizedVaxError when the client does not have permissions for the given vacc type"""
        imms = json.loads(create_covid_immunization(self.TEST_IMMUNISATION_ID).json())
        identifier = Identifier(system=imms["identifier"][0]["system"], value=imms["identifier"][0]["value"])
        self.mock_redis.hget.return_value = "FLU"
        self.mock_redis_getter.return_value = self.mock_redis
        self.authoriser.authorise.return_value = False
        self.imms_repo.get_immunization_resource_and_metadata_by_id.return_value = (
            imms,
            ImmunizationRecordMetadata(identifier=identifier, resource_version=2, is_deleted=False, is_reinstated=False),
        )

        # When
        with self.assertRaises(UnauthorizedVaxError):
            self.fhir_service.delete_immunization(self.TEST_IMMUNISATION_ID, "Test")

        # Then
        self.imms_repo.get_immunization_resource_and_metadata_by_id.assert_called_once_with(self.TEST_IMMUNISATION_ID)
        self.imms_repo.delete_immunization.assert_not_called()
        self.authoriser.authorise.assert_called_once_with("Test", ApiOperationCode.DELETE, {"FLU"})


class TestSearchImmunizations(TestFhirServiceBase):
    """Tests for FhirService.search_immunizations"""

    MOCK_SUPPLIER_SYSTEM_NAME = "Test"

    def setUp(self):
        super().setUp()
        os.environ["IMMUNIZATION_ENV"] = "internal-dev"
        os.environ["IMMUNIZATION_BASE_PATH"] = "immunisation-fhir-api/FHIR/R4"
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.validator = create_autospec(ImmunizationValidator)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser, self.validator)
        self.nhs_search_param = "patient.identifier"
        self.vaccine_type_search_param = "-immunization.target"

    @patch("service.fhir_service.uuid4", return_value="123456789-12")
    def test_search_immunizations_returns_results_as_a_search_bundle(self, mock_uuid):
        """it should return the retrieved immunization resources within a search bundle"""
        mock_resource = create_covid_immunization_dict("1234-some-id")
        vaccine_type = "COVID"
        self.authoriser.filter_permitted_vacc_types.return_value = {vaccine_type}
        self.imms_repo.find_immunizations.return_value = [mock_resource]

        # When
        result = self.fhir_service.search_immunizations(
            VALID_NHS_NUMBER, {vaccine_type}, self.MOCK_SUPPLIER_SYSTEM_NAME, None, None, None
        )

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(VALID_NHS_NUMBER, {vaccine_type})
        mock_uuid.assert_called_once()
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {"COVID"}
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 1)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?immunization-target"
                "=COVID&patient.identifier=https://fhir.nhs.uk/Id/nhs-number|9990548609",
            ),
        )
        # Will contain the matched immunization and then the referenced patient resource
        self.assertEqual(len(result.entry), 2)
        self.assertEqual(result.entry[0].resource.json(), json.dumps(ValidValues.expected_resource_in_search))
        self.assertEqual(result.entry[-1].resource.resource_type, "Patient")

    @patch("service.fhir_service.uuid4", return_value="123456789-12")
    def test_search_immunizations_filters_by_date_and_status(self, mock_uuid):
        """it should only return the resources which occurred within the date filters and have a status of completed"""
        mock_resource = create_covid_immunization_dict("1234-some-id", occurrence_date_time="2021-02-07T13:28:17+00:00")
        mock_resource_filtered_date_from = create_covid_immunization_dict(
            "1235-some-id", occurrence_date_time="2021-02-01T13:28:17+00:00"
        )
        mock_resource_filtered_date_to = create_covid_immunization_dict(
            "1236-some-id", occurrence_date_time="2023-02-07T13:28:17+00:00"
        )
        mock_resource_filtered_status = create_covid_immunization_dict("1237-some-id", status="entered-in-error")

        vaccine_type = "COVID"
        self.authoriser.filter_permitted_vacc_types.return_value = {vaccine_type}
        self.imms_repo.find_immunizations.return_value = [
            mock_resource_filtered_date_from,
            mock_resource,
            mock_resource_filtered_date_to,
            mock_resource_filtered_status,
        ]

        # When
        result = self.fhir_service.search_immunizations(
            VALID_NHS_NUMBER,
            {vaccine_type},
            self.MOCK_SUPPLIER_SYSTEM_NAME,
            datetime.date(2021, 2, 6),
            datetime.date(2023, 1, 1),
            None,
        )

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(VALID_NHS_NUMBER, {vaccine_type})
        mock_uuid.assert_called_once()
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {"COVID"}
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 1)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?-date.from=2021"
                "-02-06&-date.to=2023-01-01&immunization-target=COVID&patient.identifier="
                "https://fhir.nhs.uk/Id/nhs-number|9990548609",
            ),
        )
        # Will contain the matched immunization and then the referenced patient resource
        # And will filter out any additional resources
        self.assertEqual(len(result.entry), 2)
        self.assertEqual(result.entry[0].resource.json(), json.dumps(ValidValues.expected_resource_in_search))
        self.assertEqual(result.entry[-1].resource.resource_type, "Patient")

    @patch("service.fhir_service.uuid4", return_value="123456789-12")
    def test_search_immunizations_adds_include_to_searched_url(self, mock_uuid):
        """it should add the _include parameter into the returned url when the client provides it. Currently, it has no
        effect on the resources returned as we always include the patient resource anyway"""
        mock_resource = create_covid_immunization_dict("1234-some-id")
        vaccine_type = "COVID"
        self.authoriser.filter_permitted_vacc_types.return_value = {vaccine_type}
        self.imms_repo.find_immunizations.return_value = [mock_resource]

        # When
        result = self.fhir_service.search_immunizations(
            VALID_NHS_NUMBER, {vaccine_type}, self.MOCK_SUPPLIER_SYSTEM_NAME, None, None, "Patient.identifier"
        )

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(VALID_NHS_NUMBER, {vaccine_type})
        mock_uuid.assert_called_once()
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {"COVID"}
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 1)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?immunization-target"
                "=COVID&_include=Patient.identifier&patient.identifier=https://fhir.nhs.uk/Id/nhs-number|9990548609",
            ),
        )
        # Will contain the matched immunization and then the referenced patient resource
        self.assertEqual(len(result.entry), 2)
        self.assertEqual(result.entry[0].resource.json(), json.dumps(ValidValues.expected_resource_in_search))
        self.assertEqual(result.entry[-1].resource.resource_type, "Patient")

    def test_search_immunizations_returns_empty_bundle_when_no_results_found(self):
        """it should return an empty search bundle when no results are found"""
        vaccine_type = "FLU"
        self.authoriser.filter_permitted_vacc_types.return_value = {vaccine_type}
        self.imms_repo.find_immunizations.return_value = []

        # When
        result = self.fhir_service.search_immunizations(
            VALID_NHS_NUMBER, {vaccine_type}, self.MOCK_SUPPLIER_SYSTEM_NAME, None, None, None
        )

        # Then
        self.imms_repo.find_immunizations.assert_called_once_with(VALID_NHS_NUMBER, {vaccine_type})
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {vaccine_type}
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 0)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?immunization-target"
                "=FLU&patient.identifier=https://fhir.nhs.uk/Id/nhs-number|9990548609",
            ),
        )
        self.assertEqual(len(result.entry), 0)

    @patch("service.fhir_service.uuid4", return_value="123456789-12")
    def test_search_immunizations_includes_an_error_outcome_within_results_if_client_requests_unauthorised_vacc_types(
        self, mock_uuid
    ):
        """it should return any vaccinations that the client is authorised to retrieve but also include an Operation
        Outcome with an error if the requested anything they were not permitted to handle"""
        mock_resource = create_covid_immunization_dict("1234-some-id")
        vaccine_type = "COVID"
        self.authoriser.filter_permitted_vacc_types.return_value = {vaccine_type}
        self.imms_repo.find_immunizations.return_value = [mock_resource]

        # When
        result = self.fhir_service.search_immunizations(
            VALID_NHS_NUMBER, {vaccine_type, "FLU"}, self.MOCK_SUPPLIER_SYSTEM_NAME, None, None, None
        )

        # Then
        # Does not pass FLU in as client is only permitted to retrieve COVID vaccinations
        self.imms_repo.find_immunizations.assert_called_once_with(VALID_NHS_NUMBER, {vaccine_type})
        mock_uuid.assert_called_once()
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {"COVID", "FLU"}
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 1)
        self.assertEqual(
            result.link[0],
            BundleLink.construct(
                relation="self",
                url="https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4/Immunization?immunization-target"
                "=COVID&patient.identifier=https://fhir.nhs.uk/Id/nhs-number|9990548609",
            ),
        )
        # Will contain the matched immunization, the referenced patient resource and an OperationOutcome
        self.assertEqual(len(result.entry), 3)
        self.assertEqual(result.entry[0].resource.json(), json.dumps(ValidValues.expected_resource_in_search))
        self.assertEqual(result.entry[1].resource.resource_type, "Patient")
        self.assertEqual(result.entry[2].resource.resource_type, "OperationOutcome")

    def test_search_raises_unauthorised_error_if_no_permissions(self):
        """it should raise an UnauthorisedVaxError if the supplier does not have permissions for ANY of the requested
        vaccination types"""
        vaccine_type = "COVID"
        self.authoriser.filter_permitted_vacc_types.return_value = {}

        # When
        with self.assertRaises(UnauthorizedVaxError):
            self.fhir_service.search_immunizations(
                VALID_NHS_NUMBER, {vaccine_type}, self.MOCK_SUPPLIER_SYSTEM_NAME, None, None, None
            )

        # Then
        self.authoriser.filter_permitted_vacc_types.assert_called_once_with(
            self.MOCK_SUPPLIER_SYSTEM_NAME, ApiOperationCode.SEARCH, {vaccine_type}
        )
        self.imms_repo.find_immunizations.assert_not_called()
