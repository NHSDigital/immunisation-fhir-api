import unittest
import uuid
from copy import deepcopy
from unittest.mock import Mock, create_autospec
from .immunization_utils import  create_covid_19_immunization_dict_no_id
from models.errors import CustomValidationError
from models.fhir_immunization import ImmunizationValidator
from fhir_batch_repository import ImmunizationBatchRepository
from fhir_batch_service import ImmunizationBatchService

class TestCreateImmunizationBatchService(unittest.TestCase):

    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_validator = create_autospec(ImmunizationValidator)
        self.mock_table = Mock()
        self.service = ImmunizationBatchService(self.mock_repo, self.mock_validator)
        self.pre_validate_fhir_service = ImmunizationBatchService(
            self.mock_repo, ImmunizationValidator(add_post_validators=False)
        )

    def test_create_immunization_valid(self):
        """it should create Immunization and return imms id location"""

        imms_id = str(uuid.uuid4())
        self.mock_repo.create_immunization.return_value = imms_id
        result = self.service.create_immunization(
            immunization=create_covid_19_immunization_dict_no_id(), 
            supplier_system="test_supplier", 
            vax_type="test_vax", 
            table=self.mock_table, 
            is_present=True
        )
        self.assertEqual(result, imms_id)

    def test_create_immunization_pre_validation_error(self):
        """it should return error since it got failed in initial validation"""

        imms = create_covid_19_immunization_dict_no_id()
        imms["status"] = "not-completed"
        expected_msg = "Validation errors: status must be one of the following: completed"
        with self.assertRaises(CustomValidationError) as error:
            self.pre_validate_fhir_service.create_immunization(
                immunization=imms, 
                supplier_system="test_supplier", 
                vax_type="test_vax", 
                table=self.mock_table, 
                is_present=True
            )
        self.assertTrue(expected_msg in error.exception.message)
        self.mock_repo.create_immunization.assert_not_called() 

    def test_create_immunization_post_validation_error(self):
        """it should return error since it got failed in initial validation"""
        
        valid_imms = create_covid_19_immunization_dict_no_id()
        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        expected_msg = "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - ['bad-code'] is not a valid combination of disease codes for this service"
        with self.assertRaises(CustomValidationError) as error:
            self.pre_validate_fhir_service.create_immunization(
                immunization=bad_target_disease_imms, 
                supplier_system="test_supplier", 
                vax_type="test_vax", 
                table=self.mock_table, 
                is_present=True
            )
        self.assertTrue(expected_msg in error.exception.message)
        self.mock_repo.create_immunization.assert_not_called() 


class TestUpdateImmunizationBatchService(unittest.TestCase):

    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_validator = create_autospec(ImmunizationValidator)
        self.mock_table = Mock()
        self.service = ImmunizationBatchService(self.mock_repo, self.mock_validator)
        self.pre_validate_fhir_service = ImmunizationBatchService(
            self.mock_repo, ImmunizationValidator(add_post_validators=False)
        )

    def test_update_immunization_valid(self):
        """it should update Immunization and return imms id"""

        imms_id = str(uuid.uuid4())
        self.mock_repo.update_immunization.return_value = imms_id
        result = self.service.update_immunization(
            immunization=create_covid_19_immunization_dict_no_id(), 
            supplier_system="test_supplier", 
            vax_type="test_vax", 
            table=self.mock_table, 
            is_present=True
        )
        self.assertEqual(result, imms_id)

    def test_update_immunization_pre_validation_error(self):
        """it should return error since it got failed in initial validation"""

        imms = create_covid_19_immunization_dict_no_id()
        imms["status"] = "not-completed"
        expected_msg = "Validation errors: status must be one of the following: completed"
        with self.assertRaises(CustomValidationError) as error:
            self.pre_validate_fhir_service.update_immunization(
                immunization=imms, 
                supplier_system="test_supplier", 
                vax_type="test_vax", 
                table=self.mock_table, 
                is_present=True
            )
        self.assertTrue(expected_msg in error.exception.message)
        self.mock_repo.update_immunization.assert_not_called() 

    def test_update_immunization_post_validation_error(self):
        """it should return error since it got failed in initial validation"""

        valid_imms = create_covid_19_immunization_dict_no_id()
        bad_target_disease_imms = deepcopy(valid_imms)
        bad_target_disease_imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = "bad-code"
        expected_msg = "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - ['bad-code'] is not a valid combination of disease codes for this service"
        with self.assertRaises(CustomValidationError) as error:
            self.pre_validate_fhir_service.update_immunization(
                immunization=bad_target_disease_imms, 
                supplier_system="test_supplier", 
                vax_type="test_vax", 
                table=self.mock_table, 
                is_present=True
            )
        self.assertTrue(expected_msg in error.exception.message)
        self.mock_repo.update_immunization.assert_not_called()


class TestDeleteImmunizationBatchService(unittest.TestCase):

    def setUp(self):
        self.mock_repo = create_autospec(ImmunizationBatchRepository)
        self.mock_validator = create_autospec(ImmunizationValidator)
        self.mock_table = Mock()
        self.service = ImmunizationBatchService(self.mock_repo, self.mock_validator)
        self.pre_validate_fhir_service = ImmunizationBatchService(
            self.mock_repo, ImmunizationValidator(add_post_validators=False)
        )

    def test_delete_immunization_valid(self):
        """it should delete Immunization and return imms id"""

        imms_id = str(uuid.uuid4())
        self.mock_repo.delete_immunization.return_value = imms_id
        result = self.service.delete_immunization(
            immunization=create_covid_19_immunization_dict_no_id(), 
            supplier_system="test_supplier", 
            vax_type="test_vax", 
            table=self.mock_table, 
            is_present=True
        )
        self.assertEqual(result, imms_id)            



if __name__ == '__main__':
    unittest.main()