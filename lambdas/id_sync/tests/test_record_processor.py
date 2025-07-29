import unittest
from unittest.mock import patch, MagicMock
import json

from record_processor import process_record, check_records_exist, update_patient_index, get_id
from common.aws_lambda_sqs_event_record import AwsLambdaSqsEventRecord


class TestRecordProcessor(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures and mocks"""
        # Mock logger
        self.logger_patcher = patch('record_processor.logger')
        self.mock_logger = self.logger_patcher.start()

        # Mock external dependencies
        self.get_pds_patient_details_patcher = patch('record_processor.get_pds_patient_details')
        self.mock_get_pds_patient_details = self.get_pds_patient_details_patcher.start()

        # Test data
        self.test_event_body = {"subject": "9912003888"}
        self.test_event_body_json = json.dumps(self.test_event_body)
        self.test_id = "9912003888"

        # Create test SQS event record
        self.test_sqs_record = MagicMock(spec=AwsLambdaSqsEventRecord)
        self.test_sqs_record.body = self.test_event_body

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()


class TestProcessRecord(TestRecordProcessor):

    def test_process_record_success_no_update_required(self):
        """Test successful processing when patient ID matches"""
        # Arrange
        with patch('record_processor.get_id', return_value=self.test_id), \
             patch('record_processor.check_records_exist', return_value=True):

            self.mock_get_pds_patient_details.return_value = {"id": self.test_id}

            # Act
            result = process_record(self.test_sqs_record)

            # Assert
            expected_result = {"status": "success", "message": "No update required"}
            self.assertEqual(result, expected_result)

            # Verify calls
            self.mock_logger.info.assert_called_with("Processing record: %s", self.test_sqs_record)
            self.mock_get_pds_patient_details.assert_called_once_with(self.test_id)

    def test_process_record_success_update_required(self):
        """Test successful processing when patient ID differs"""
        # Arrange
        new_id = "9912003999"

        with patch('record_processor.get_id', return_value=self.test_id), \
             patch('record_processor.check_records_exist', return_value=True), \
             patch('record_processor.update_patient_index') as mock_update:

            self.mock_get_pds_patient_details.return_value = {"id": new_id}
            mock_update.return_value = {"status": "success",
                                        "message": f"Updated patient idx from {self.test_id} to {new_id}"}

            # Act
            result = process_record(self.test_sqs_record)

            # Assert
            expected_result = {"status": "success", "message": f"Updated patient idx from {self.test_id} to {new_id}"}
            self.assertEqual(result, expected_result)

            # Verify calls
            mock_update.assert_called_once_with(self.test_id, new_id)
            self.mock_get_pds_patient_details.assert_called_once_with(self.test_id)

    def test_process_record_no_records_exist(self):
        """Test when no records exist for the patient ID"""
        # Arrange
        with patch('record_processor.get_id', return_value=self.test_id), \
             patch('record_processor.check_records_exist', return_value=False):

            # Act
            result = process_record(self.test_sqs_record)

            # Assert
            expected_result = {"status": "error", "message": f"No records found for ID: {self.test_id}"}
            self.assertEqual(result, expected_result)

            # Verify PDS was not called
            self.mock_get_pds_patient_details.assert_not_called()

    def test_process_record_pds_returns_none_id(self):
        """Test when PDS returns patient details without ID"""
        # Arrange
        with patch('record_processor.get_id', return_value=self.test_id), \
             patch('record_processor.check_records_exist', return_value=True):

            self.mock_get_pds_patient_details.return_value = {}

            # Act & Assert
            result = process_record(self.test_sqs_record)
            expected_result = {"status": "error", "message": f"No records returned for ID: {self.test_id}"}
            self.assertEqual(result, expected_result)

    def test_process_record_get_id_returns_none(self):
        """Test when get_id returns None"""
        # Arrange
        with patch('record_processor.get_id', return_value=None), \
             patch('record_processor.check_records_exist') as mock_check:

            # Act
            result = process_record(self.test_sqs_record)

            # Assert
            expected_result = {"status": "error", "message": "No ID found in event record"}
            self.assertEqual(result, expected_result)

            # Verify check_records_exist was called with None
            mock_check.assert_not_called()


class TestGetId(TestRecordProcessor):

    def test_get_id_success_with_dict(self):
        """Test successful ID extraction from dict"""
        # Act
        result = get_id(self.test_event_body)

        # Assert
        self.assertEqual(result, self.test_id)

    def test_get_id_success_with_json_string(self):
        """Test successful ID extraction from JSON string"""
        # Act
        result = get_id(self.test_event_body_json)

        # Assert
        self.assertEqual(result, self.test_id)

    def test_get_id_missing_subject(self):
        """Test when subject field is missing"""
        # Arrange
        event_body = {"other_field": "value"}

        # Act
        result = get_id(event_body)

        # Assert
        self.assertIsNone(result)

    def test_get_id_invalid_json(self):
        """Test with invalid JSON string"""
        # Arrange
        invalid_json = "{'invalid': json}"

        # Act
        result = get_id(invalid_json)

        # Assert
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()

    def test_get_id_none_input(self):
        """Test with None input"""
        # Act
        result = get_id(None)

        # Assert
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_once()

    def test_get_id_empty_dict(self):
        """Test with empty dict"""
        # Act
        result = get_id({})

        # Assert
        self.assertIsNone(result)


class TestCheckRecordsExist(TestRecordProcessor):

    def test_check_records_exist_always_returns_false(self):
        ''' TODO placeholder test for check_records_exist '''
        # Act
        result = check_records_exist(self.test_id)

        # Assert
        self.assertTrue(result)


class TestUpdatePatientIndex(TestRecordProcessor):

    def test_update_patient_index_success(self):
        """ TODO placeholder test for update_patient_index """
        # Arrange
        old_id = "9912003888"
        new_id = "9912003999"

        # Act
        result = update_patient_index(old_id, new_id)

        # Assert
        expected_result = {
            "status": "success",
            "message": f"Updated patient idx from {old_id} to {new_id}",
            "TODO": "Implement logic"
        }
        self.assertEqual(result, expected_result)

    def test_update_patient_index_with_empty_strings(self):
        """Test update with empty string IDs"""
        # Act
        result = update_patient_index("", "")

        # Assert
        expected_result = {
            "status": "success",
            "message": "Updated patient idx from  to ",
            "TODO": "Implement logic"
        }
        self.assertEqual(result, expected_result)


class TestIntegration(TestRecordProcessor):

    def test_full_process_flow_with_mocked_functions(self):
        """Integration test of the full process flow"""
        # Arrange
        new_id = "9912003999"

        with patch('record_processor.get_id') as mock_get_id, \
             patch('record_processor.check_records_exist') as mock_check, \
             patch('record_processor.update_patient_index') as mock_update:

            mock_get_id.return_value = self.test_id
            mock_check.return_value = True
            self.mock_get_pds_patient_details.return_value = {"id": new_id}
            mock_update.return_value = {"status": "success", "message": "Updated"}

            # Act
            result = process_record(self.test_sqs_record)

            # Assert
            self.assertEqual(result, {"status": "success", "message": "Updated"})

            # Verify call chain
            mock_get_id.assert_called_once_with(self.test_sqs_record.body)
            mock_check.assert_called_once_with(self.test_id)
            self.mock_get_pds_patient_details.assert_called_once_with(self.test_id)
            mock_update.assert_called_once_with(self.test_id, new_id)

    def test_error_propagation_from_pds_service(self):
        """Test error propagation when PDS service fails"""
        # Arrange
        with patch('record_processor.get_id', return_value=self.test_id), \
             patch('record_processor.check_records_exist', return_value=True):

            self.mock_get_pds_patient_details.side_effect = Exception("PDS API Error")

            # Act & Assert
            with self.assertRaises(Exception) as context:
                process_record(self.test_sqs_record)

            self.assertEqual(str(context.exception), "PDS API Error")
