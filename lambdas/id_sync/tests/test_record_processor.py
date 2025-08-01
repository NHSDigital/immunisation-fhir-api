import unittest
from unittest.mock import patch
from record_processor import process_record


class TestRecordProcessor(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures and mocks"""
        self.logger_patcher = patch('record_processor.logger')
        self.mock_logger = self.logger_patcher.start()

        self.pds_get_patient_id_patcher = patch('record_processor.pds_get_patient_id')
        self.mock_pds_get_patient_id = self.pds_get_patient_id_patcher.start()

        self.ieds_check_exist_patcher = patch('record_processor.ieds_check_exist')
        self.mock_ieds_check_exist = self.ieds_check_exist_patcher.start()

        self.ieds_update_patient_id_patcher = patch('record_processor.ieds_update_patient_id')
        self.mock_ieds_update_patient_id = self.ieds_update_patient_id_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_process_record_success_no_update_required(self):
        """Test successful processing when patient ID matches"""
        # Arrange
        test_id = "54321"
        with patch('record_processor.ieds_check_exist', return_value=True):

            test_record = {"body": {"subject": test_id}}
            self.mock_pds_get_patient_id.return_value = test_id

            # Act
            result = process_record(test_record)

            # Assert
            self.assertEqual(result["nhs_number"], test_id)
            self.assertEqual(result["message"], "No update required")
            self.assertEqual(result["status"], "success")

            # Verify calls
            self.mock_pds_get_patient_id.assert_called_once_with(test_id)

    def test_process_record_success_update_required(self):
        """Test successful processing when patient ID differs"""
        # Arrange
        pds_id = "pds-id-1"
        nhs_number = "nhs-number-1"

        test_sqs_record = {"body": {"subject": nhs_number}}
        self.mock_pds_get_patient_id.return_value = pds_id
        success_response = {"status": "success"}
        self.mock_ieds_update_patient_id.return_value = success_response
        # Act
        result = process_record(test_sqs_record)

        # Assert
        expected_result = success_response
        self.assertEqual(result, expected_result)

        # Verify calls
        self.mock_pds_get_patient_id.assert_called_once_with(nhs_number)

    def test_process_record_no_records_exist(self):
        """Test when no records exist for the patient ID"""

        # Arrange
        test_id = "12345"
        with patch('record_processor.ieds_check_exist', return_value=False):

            # Act
            test_record = {"body": {"subject": test_id}}
            result = process_record(test_record)

            # Assert
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["message"], f"No records returned for ID: {test_id}")

            # Verify PDS was not called
            self.mock_pds_get_patient_id.assert_called_once()

    def test_process_record_pds_returns_none_id(self):
        """Test when PDS returns none """
        # Arrange
        test_id = "12345a"
        self.mock_pds_get_patient_id.return_value = None
        test_record = {"body": {"subject": test_id}}
        # Act & Assert
        result = process_record(test_record)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], f"No patient ID found for NHS number: {test_id}")
        self.mock_ieds_check_exist.assert_not_called()
        self.mock_ieds_update_patient_id.assert_not_called()

    def test_process_record_ieds_returns_false(self):
        """Test when id doesnt exist in IEDS"""
        # Arrange
        test_id = "12345a"
        pds_id = "pds-id-1"
        self.mock_pds_get_patient_id.return_value = pds_id
        self.mock_ieds_check_exist.return_value = False
        # Act & Assert
        result = process_record({"body": {"subject": test_id}})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], f"No records returned for ID: {test_id}")

    def test_body_is_string(self):
        """Test processing a simple record"""
        # Arrange
        test_record = {"body": "{'subject': 'nhs-number-1'}"}
        new_test_id = "nhs-number-2"

        self.mock_pds_get_patient_id.return_value = new_test_id
        self.mock_ieds_update_patient_id.return_value = {"status": "success"}
        # Act
        result = process_record(test_record)

        # Assert
        self.assertEqual(result["status"], "success")
