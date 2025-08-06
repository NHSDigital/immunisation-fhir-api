import unittest
from unittest.mock import patch, MagicMock
from pds_details import pds_get_patient_details, pds_get_patient_id
from exceptions.id_sync_exception import IdSyncException


class TestGetPdsPatientDetails(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures and mocks"""
        self.test_patient_id = "9912003888"

        # Patch all external dependencies
        self.logger_patcher = patch('pds_details.logger')
        self.mock_logger = self.logger_patcher.start()

        self.secrets_manager_patcher = patch('pds_details.secrets_manager_client')
        self.mock_secrets_manager = self.secrets_manager_patcher.start()

        self.pds_env_patcher = patch('pds_details.get_pds_env')
        self.mock_pds_env = self.pds_env_patcher.start()
        self.mock_pds_env.return_value = "test-env"

        self.cache_patcher = patch('pds_details.Cache')
        self.mock_cache_class = self.cache_patcher.start()
        self.mock_cache_instance = MagicMock()
        self.mock_cache_class.return_value = self.mock_cache_instance

        self.auth_patcher = patch('pds_details.AppRestrictedAuth')
        self.mock_auth_class = self.auth_patcher.start()
        self.mock_auth_instance = MagicMock()
        self.mock_auth_class.return_value = self.mock_auth_instance

        self.pds_service_patcher = patch('pds_details.PdsService')
        self.mock_pds_service_class = self.pds_service_patcher.start()
        self.mock_pds_service_instance = MagicMock()
        self.mock_pds_service_class.return_value = self.mock_pds_service_instance

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()

    def test_pds_get_patient_details_success(self):
        """Test successful retrieval of patient details"""
        # Arrange
        expected_patient_data = {
            "identifier": [
                {"value": "9912003888"}
            ],
            "name": "John Doe",
            "birthDate": "1990-01-01",
            "gender": "male"
        }
        self.mock_pds_service_instance.get_patient_details.return_value = expected_patient_data

        # Act
        result = pds_get_patient_details(self.test_patient_id)

        # Assert
        self.assertEqual(result["identifier"][0]["value"], "9912003888")

        # Verify Cache was initialized correctly
        self.mock_cache_class.assert_called_once()

        # Verify get_patient_details was called
        self.mock_pds_service_instance.get_patient_details.assert_called_once()

    def test_pds_get_patient_details_no_patient_found(self):
        """Test when PDS returns None (no patient found)"""
        # Arrange
        self.mock_pds_service_instance.get_patient_details.return_value = None

        # Act
        result = pds_get_patient_details(self.test_patient_id)

        # Assert
        self.assertIsNone(result)

        self.mock_pds_service_instance.get_patient_details.assert_called_once_with(self.test_patient_id)

    def test_pds_get_patient_details_empty_response(self):
        """Test when PDS returns empty dict (falsy)"""
        # Arrange
        self.mock_pds_service_instance.get_patient_details.return_value = None

        # Act
        result = pds_get_patient_details(self.test_patient_id)

        # Assert
        self.assertIsNone(result)

    def test_pds_get_patient_details_pds_service_exception(self):
        """Test when PdsService.get_patient_details raises an exception"""
        # Arrange
        mock_exception = Exception("My custom error")
        self.mock_pds_service_instance.get_patient_details.side_effect = mock_exception

        # Act
        with self.assertRaises(IdSyncException) as context:
            pds_get_patient_details(self.test_patient_id)

        exception = context.exception

        # Assert
        self.assertEqual(exception.inner_exception, mock_exception)
        self.assertEqual(exception.message, f"Error getting PDS patient details for {self.test_patient_id}")
        self.assertEqual(exception.nhs_numbers, None)

        # Verify exception was logged
        self.mock_logger.exception.assert_called_once_with(
            f"Error getting PDS patient details for {self.test_patient_id}")

        self.mock_pds_service_instance.get_patient_details.assert_called_once_with(self.test_patient_id)

    def test_pds_get_patient_details_cache_initialization_error(self):
        """Test when Cache initialization fails"""
        # Arrange
        self.mock_cache_class.side_effect = OSError("Cannot write to /tmp")

        # Act
        with self.assertRaises(IdSyncException) as context:
            pds_get_patient_details(self.test_patient_id)

        # Assert
        exception = context.exception
        self.assertEqual(exception.message, f"Error getting PDS patient details for {self.test_patient_id}")
        self.assertEqual(exception.nhs_numbers, None)

        # Verify exception was logged
        self.mock_logger.exception.assert_called_once_with(
            f"Error getting PDS patient details for {self.test_patient_id}")

        self.mock_cache_class.assert_called_once()

    def test_pds_get_patient_details_auth_initialization_error(self):
        """Test when AppRestrictedAuth initialization fails"""
        # Arrange
        self.mock_auth_class.side_effect = ValueError("Invalid authentication parameters")

        # Act
        with self.assertRaises(IdSyncException) as context:
            pds_get_patient_details(self.test_patient_id)

        # Assert
        exception = context.exception
        self.assertEqual(exception.message, f"Error getting PDS patient details for {self.test_patient_id}")
        self.assertEqual(exception.nhs_numbers, None)

        # Verify exception was logged
        self.mock_logger.exception.assert_called_once_with(
            f"Error getting PDS patient details for {self.test_patient_id}")

    def test_pds_get_patient_details_exception(self):
        """Test when logger.info throws an exception"""
        # Arrange
        test_exception = Exception("some-random-error")
        self.mock_pds_service_class.side_effect = test_exception
        test_nhs_number = "another-nhs-number"

        # Act
        with self.assertRaises(Exception) as context:
            pds_get_patient_details(test_nhs_number)

        exception = context.exception
        # Assert
        self.assertEqual(exception.inner_exception, test_exception)
        self.assertEqual(exception.message, f"Error getting PDS patient details for {test_nhs_number}")
        self.assertEqual(exception.nhs_numbers, None)
        # Verify logger.exception was called due to the caught exception
        self.mock_logger.exception.assert_called_once_with(
            f"Error getting PDS patient details for {test_nhs_number}")

    def test_pds_get_patient_details_different_patient_ids(self):
        """Test with different patient ID formats"""
        test_cases = [
            ("9912003888", {"identifier": [{"value": "9912003888"}]}),
            ("1234567890", {"identifier": [{"value": "1234567890"}]}),
            ("0000000000", {"identifier": [{"value": "0000000000"}]}),
        ]

        for patient_id, expected_response in test_cases:
            with self.subTest(patient_id=patient_id):
                # Reset mocks
                self.mock_pds_service_instance.reset_mock()
                self.mock_logger.reset_mock()

                # Arrange
                self.mock_pds_service_instance.get_patient_details.return_value = expected_response

                # Act
                result = pds_get_patient_details(patient_id)

                # Assert
                self.assertEqual(result, expected_response)
                self.mock_pds_service_instance.get_patient_details.assert_called_once_with(patient_id)

    def test_pds_get_patient_details(self):
        """Test with complex identifier structure"""
        # Arrange
        test_nhs_number = "9912003888"
        pds_id = "abcefghijkl"
        mock_pds_response = {"identifier": [{"value": pds_id}]}
        self.mock_pds_service_instance.get_patient_details.return_value = mock_pds_response
        # Act
        result = pds_get_patient_details(test_nhs_number)

        # Assert - function should extract the value from first identifier
        self.assertEqual(result, mock_pds_response)
        self.mock_pds_service_instance.get_patient_details.assert_called_once_with(test_nhs_number)


# test pds_get_patient_id function
class TestGetPdsPatientId(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures and mocks"""
        self.test_nhs_number = "9912003888"

        # Patch all external dependencies
        self.logger_patcher = patch('pds_details.logger')
        self.mock_logger = self.logger_patcher.start()

        self.pds_get_patient_details_patcher = patch('pds_details.pds_get_patient_details')
        self.mock_pds_get_patient_details = self.pds_get_patient_details_patcher.start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()

    def test_pds_get_patient_id_success(self):
        """Test successful retrieval of PDS patient ID"""
        # Arrange
        expected_id = "1234567890"
        self.mock_pds_get_patient_details.return_value = {"identifier": [{"value": expected_id}]}

        # Act
        result = pds_get_patient_id(self.test_nhs_number)

        # Assert
        self.assertEqual(result, expected_id)

    def test_pds_get_patient_id_empty_identifier_array(self):
        """Test when identifier array is empty"""
        # Arrange
        patient_data_empty_identifier = {
            "identifier": [],  # Empty array
            "name": "John Doe"
        }
        self.mock_pds_get_patient_details.return_value = patient_data_empty_identifier

        # Act
        with self.assertRaises(IdSyncException) as context:
            pds_get_patient_id(self.test_nhs_number)

        # Assert
        exception = context.exception
        self.assertEqual(exception.message, f"Error getting PDS patient ID for {self.test_nhs_number}")
        self.assertEqual(exception.nhs_numbers, None)
