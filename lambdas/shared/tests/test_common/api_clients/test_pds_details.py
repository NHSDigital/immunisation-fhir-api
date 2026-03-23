import unittest
from unittest.mock import MagicMock, patch

from common.api_clients.errors import PdsSyncException
from common.api_clients.get_pds_details import get_pds_service, pds_get_patient_details


class TestGetPdsPatientDetails(unittest.TestCase):
    def setUp(self):
        self.test_patient_id = "9912003888"
        get_pds_service.__globals__["_pds_service"] = None

        self.logger_patcher = patch("common.api_clients.get_pds_details.logger")
        self.mock_logger = self.logger_patcher.start()

        self.auth_patcher = patch("common.api_clients.get_pds_details.AppRestrictedAuth")
        self.mock_auth_class = self.auth_patcher.start()
        self.mock_auth_instance = MagicMock()
        self.mock_auth_class.return_value = self.mock_auth_instance

        self.pds_service_patcher = patch("common.api_clients.get_pds_details.PdsService")
        self.mock_pds_service_class = self.pds_service_patcher.start()
        self.mock_pds_service_instance = MagicMock()
        self.mock_pds_service_class.return_value = self.mock_pds_service_instance

    def tearDown(self):
        get_pds_service.__globals__["_pds_service"] = None
        patch.stopall()

    def test_pds_get_patient_details_success(self):
        expected_patient_data = {
            "identifier": [{"value": "9912003888"}],
            "name": "John Doe",
            "birthDate": "1990-01-01",
            "gender": "male",
        }
        self.mock_pds_service_instance.get_patient_details.return_value = expected_patient_data

        result = pds_get_patient_details(self.test_patient_id)

        self.assertEqual(result["identifier"][0]["value"], "9912003888")
        self.mock_auth_class.assert_called_once()
        self.mock_pds_service_class.assert_called_once()

    def test_pds_get_patient_details_no_patient_found(self):
        self.mock_pds_service_instance.get_patient_details.return_value = None

        result = pds_get_patient_details(self.test_patient_id)

        self.assertIsNone(result)
        self.mock_pds_service_instance.get_patient_details.assert_called_once_with(self.test_patient_id)

    def test_pds_get_patient_details_pds_service_exception(self):
        mock_exception = Exception("My custom error")
        self.mock_pds_service_instance.get_patient_details.side_effect = mock_exception

        with self.assertRaises(PdsSyncException) as context:
            pds_get_patient_details(self.test_patient_id)

        exception = context.exception

        self.assertEqual(
            exception.message,
            "Error retrieving patient details from PDS",
        )

        self.mock_logger.exception.assert_called_once_with("Error retrieving patient details from PDS")
        self.mock_pds_service_instance.get_patient_details.assert_called_once_with(self.test_patient_id)

    def test_pds_get_patient_details_auth_initialization_error(self):
        self.mock_auth_class.side_effect = ValueError("Invalid authentication parameters")

        with self.assertRaises(PdsSyncException) as context:
            pds_get_patient_details(self.test_patient_id)

        exception = context.exception
        self.assertEqual(
            exception.message,
            "Error retrieving patient details from PDS",
        )

        self.mock_logger.exception.assert_called_once_with("Error retrieving patient details from PDS")

    def test_reuses_same_pds_service_instance(self):
        pds_get_patient_details("1111111111")
        pds_get_patient_details("2222222222")

        self.mock_auth_class.assert_called_once()
        self.mock_pds_service_class.assert_called_once()
        self.assertEqual(self.mock_pds_service_instance.get_patient_details.call_count, 2)
