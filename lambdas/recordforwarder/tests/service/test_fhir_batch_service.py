import json
import unittest
import uuid
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, create_autospec, patch

from common.models.errors import CustomValidationError
from common.models.fhir_immunization import ImmunizationValidator
from repository.fhir_batch_repository import ImmunizationBatchRepository
from service.fhir_batch_service import ImmunizationBatchService
from test_common.testing_utils.immunization_utils import VALID_NHS_NUMBER, create_covid_immunization_dict_no_id
from test_common.validator.testing_utils.csv_fhir_utils import parse_test_file

# Constants for use within the tests
VALID_ODS_ORGANIZATION_CODE = "RJC02"


class TestFhirBatchServiceBase(unittest.TestCase):
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

    def create_covid_immunization_dict(
        self, imms_id=None, nhs_number=VALID_NHS_NUMBER, occurrence_date_time="2021-02-07T13:28:17+00:00", code=None
    ):
        if imms_id is not None:
            imms = create_covid_immunization_dict(imms_id, nhs_number, occurrence_date_time)
        else:
            imms = create_covid_immunization_dict_no_id(nhs_number, occurrence_date_time)
        if code:
            [x for x in imms["performer"] if x["actor"].get("type") == "Organization"][0]["actor"]["identifier"][
                "value"
            ] = code
        return imms

class TestCreateImmunizationBatchService(TestFhirBatchServiceBase):
    def setUp(self):
        super().setUp()
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_table = Mock()
        self.fhir_service = ImmunizationBatchService(self.mock_repo, ImmunizationValidator())
        self.mock_validator_redis = Mock()
        self.validator_redis_getter_patcher = patch("common.models.fhir_immunization.get_redis_client")
        self.mock_validator_redis_getter = self.validator_redis_getter_patcher.start()
        # test schema file
        validation_folder = Path(__file__).resolve().parent
        self.schemaFilePath = validation_folder / "test_schemas/test_schema.json"
        self.schemaFile = parse_test_file(self.schemaFilePath)
        self.mock_validator_redis.hget.return_value = self.schemaFile
        self.mock_validator_redis_getter.return_value = self.mock_validator_redis

    def test_create_immunization_valid(self):
        """it should create Immunization and return imms id location"""

        imms_id = str(uuid.uuid4())
        self.mock_repo.create_immunization.return_value = imms_id
        # patch the ods-organization-code here, so that it doesn't fail key data validation,
        # but so that the function doesn't break other tests using the same file
        result = self.fhir_service.create_immunization(
            immunization=self.create_covid_immunization_dict(code=VALID_ODS_ORGANIZATION_CODE),
            supplier_system="test_supplier",
            vax_type="test_vax",
            table=self.mock_table,
            is_present=True,
        )
        self.assertEqual(result, imms_id)

    def test_create_immunization_pre_validation_error(self):
        """it should return error since it got failed in initial validation"""

        imms = self.create_covid_immunization_dict(code=VALID_ODS_ORGANIZATION_CODE)

        # TEMP: because the test schema does not yet check the "status" field
        imms["lotNumber"] = ""
        expected_msg = [
            {
                "code": 5,
                "message": "Value not empty failure",
                "row": 2,
                "field": "lotNumber",
                "details": "Value is empty, not as expected",
            }
        ]
        #imms["status"] = "not-completed"
        #expected_msg = "Validation errors: status must be one of the following: completed"

        with self.assertRaises(CustomValidationError) as error:
            self.fhir_service.create_immunization(
                immunization=imms,
                supplier_system="test_supplier",
                vax_type="test_vax",
                table=self.mock_table,
                is_present=True,
            )
        self.assertEqual(json.dumps(expected_msg), error.exception.message)
        self.mock_repo.create_immunization.assert_not_called()

    def test_create_immunization_post_validation_error(self):
        """it should return error since it got failed in initial validation"""

        valid_imms = self.create_covid_immunization_dict(code=VALID_ODS_ORGANIZATION_CODE)
        bad_target_disease_imms = deepcopy(valid_imms)

        # TEMP: because the test schema does not yet check the "targetDisease" field
        bad_target_disease_imms["contained"][1]["name"][0]["given"] = None
        expected_msg = [
            {
                "code": 5,
                "message": "Value not empty failure",
                "row": 2,
                "field": "contained|#:Patient|name|#:official|given|0",
                "details": "Value is empty, not as expected",
            }
        ]
        #bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        #expected_msg = "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - ['bad-code'] is not a valid combination of disease codes for this service"

        self.mock_redis.hget.return_value = None  # Reset mock for invalid cases
        self.mock_redis_getter.return_value = self.mock_redis
        with self.assertRaises(CustomValidationError) as error:
            self.fhir_service.create_immunization(
                immunization=bad_target_disease_imms,
                supplier_system="test_supplier",
                vax_type="test_vax",
                table=self.mock_table,
                is_present=True,
            )
        self.assertEqual(json.dumps(expected_msg), error.exception.message)
        self.mock_repo.create_immunization.assert_not_called()


class TestUpdateImmunizationBatchService(TestFhirBatchServiceBase):
    def setUp(self):
        super().setUp()
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_table = Mock()
        self.fhir_service = ImmunizationBatchService(self.mock_repo, ImmunizationValidator())
        self.mock_validator_redis = Mock()
        self.validator_redis_getter_patcher = patch("common.models.fhir_immunization.get_redis_client")
        self.mock_validator_redis_getter = self.validator_redis_getter_patcher.start()
        # test schema file
        validation_folder = Path(__file__).resolve().parent
        self.schemaFilePath = validation_folder / "test_schemas/test_schema.json"
        self.schemaFile = parse_test_file(self.schemaFilePath)
        self.mock_validator_redis.hget.return_value = self.schemaFile
        self.mock_validator_redis_getter.return_value = self.mock_validator_redis

    def tearDown(self):
        super().tearDown()
        self.mock_repo.reset_mock()
        self.mock_table.reset_mock()
        self.fhir_service = None

    def test_update_immunization_valid(self):
        """it should update Immunization and return imms id"""

        imms_id = str(uuid.uuid4())
        self.mock_repo.update_immunization.return_value = imms_id
        result = self.fhir_service.update_immunization(
            immunization=self.create_covid_immunization_dict(code=VALID_ODS_ORGANIZATION_CODE),
            supplier_system="test_supplier",
            vax_type="test_vax",
            table=self.mock_table,
            is_present=True,
        )
        self.assertEqual(result, imms_id)

    def test_update_immunization_pre_validation_error(self):
        """it should return error since it got failed in initial validation"""

        imms = self.create_covid_immunization_dict(code=VALID_ODS_ORGANIZATION_CODE)

        # TEMP: because the test schema does not yet check the "status" field
        imms["lotNumber"] = ""
        expected_msg = [
            {
                "code": 5,
                "message": "Value not empty failure",
                "row": 2,
                "field": "lotNumber",
                "details": "Value is empty, not as expected",
            }
        ]
        #imms["status"] = "not-completed"
        #expected_msg = "Validation errors: status must be one of the following: completed"

        with self.assertRaises(CustomValidationError) as error:
            self.fhir_service.update_immunization(
                immunization=imms,
                supplier_system="test_supplier",
                vax_type="test_vax",
                table=self.mock_table,
                is_present=True,
            )
        self.assertEqual(json.dumps(expected_msg), error.exception.message)
        self.mock_repo.update_immunization.assert_not_called()

    def test_update_immunization_post_validation_error(self):
        """it should return error since it got failed in initial validation"""

        self.mock_redis.hget.return_value = None  # Reset mock for invalid cases
        self.mock_redis_getter.return_value = self.mock_redis

        valid_imms = self.create_covid_immunization_dict(code=VALID_ODS_ORGANIZATION_CODE)
        bad_target_disease_imms = deepcopy(valid_imms)

        # TEMP: because the test schema does not yet check the "targetDisease" field
        bad_target_disease_imms["contained"][1]["name"][0]["given"] = None
        expected_msg = [
            {
                "code": 5,
                "message": "Value not empty failure",
                "row": 2,
                "field": "contained|#:Patient|name|#:official|given|0",
                "details": "Value is empty, not as expected",
            }
        ]
        #bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        #expected_msg = "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - ['bad-code'] is not a valid combination of disease codes for this service"

        with self.assertRaises(CustomValidationError) as error:
            self.fhir_service.update_immunization(
                immunization=bad_target_disease_imms,
                supplier_system="test_supplier",
                vax_type="test_vax",
                table=self.mock_table,
                is_present=True,
            )
        self.assertEqual(json.dumps(expected_msg), error.exception.message)
        self.mock_repo.update_immunization.assert_not_called()


class TestDeleteImmunizationBatchService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_validator = create_autospec(ImmunizationValidator)
        self.mock_table = Mock()
        self.fhir_service = ImmunizationBatchService(self.mock_repo, self.mock_validator)

    def test_delete_immunization_valid(self):
        """it should delete Immunization and return imms id"""

        imms_id = str(uuid.uuid4())
        self.mock_repo.delete_immunization.return_value = imms_id
        result = self.fhir_service.delete_immunization(
            immunization=create_covid_immunization_dict_no_id(),
            supplier_system="test_supplier",
            vax_type="test_vax",
            table=self.mock_table,
            is_present=True,
        )
        self.assertEqual(result, imms_id)


if __name__ == "__main__":
    unittest.main()
