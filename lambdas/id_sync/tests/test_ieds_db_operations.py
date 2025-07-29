import unittest
from unittest.mock import patch, MagicMock
from boto3.dynamodb.conditions import Key

import ieds_db_operations


class TestIedsDbOperations(unittest.TestCase):
    """Base test class for IEDS database operations"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset global table variable for each test
        ieds_db_operations.ieds_table = None

        # Mock get_ieds_table_name
        self.get_ieds_table_name_patcher = patch('ieds_db_operations.get_ieds_table_name')
        self.mock_get_ieds_table_name = self.get_ieds_table_name_patcher.start()
        self.mock_get_ieds_table_name.return_value = 'test-ieds-table'

        # Mock get_delta_table
        self.get_delta_table_patcher = patch('ieds_db_operations.get_delta_table')
        self.mock_get_delta_table = self.get_delta_table_patcher.start()

        # Create mock table
        self.mock_table = MagicMock()
        self.mock_get_delta_table.return_value = self.mock_table

        # mock logger.exception
        self.logger_patcher = patch('ieds_db_operations.logger')
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()


class TestGetIedsTable(TestIedsDbOperations):
    """Test get_ieds_table function"""

    def test_get_ieds_table_first_call(self):
        """Test first call to get_ieds_table initializes the global variable"""
        # Act
        result = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result, self.mock_table)
        self.assertEqual(ieds_db_operations.ieds_table, self.mock_table)

        # Verify function calls
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_delta_table.assert_called_once_with('test-ieds-table')

    def test_get_ieds_table_cached_call(self):
        """Test subsequent calls return cached table"""
        # Arrange - Set up cached table
        cached_table = MagicMock()
        ieds_db_operations.ieds_table = cached_table

        # Act
        result = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result, cached_table)

        # Verify no new calls were made (using cached version)
        self.mock_get_ieds_table_name.assert_not_called()
        self.mock_get_delta_table.assert_not_called()

    def test_get_ieds_table_multiple_calls_same_instance(self):
        """Test multiple calls return the same table instance"""
        # Act
        result1 = ieds_db_operations.get_ieds_table()
        result2 = ieds_db_operations.get_ieds_table()
        result3 = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertIs(result1, result2)
        self.assertIs(result2, result3)
        self.assertEqual(result1, self.mock_table)

        # Verify initialization only happened once
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_delta_table.assert_called_once()

    def test_get_ieds_table_exception_handling(self):
        """Test exception handling when table initialization fails"""
        # Arrange
        self.mock_get_delta_table.side_effect = Exception("Table initialization failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.get_ieds_table()

        self.assertEqual(str(context.exception), "Table initialization failed")

        # Verify global variable remains None after failure
        self.assertIsNone(ieds_db_operations.ieds_table)


class TestIedsCheckExists(TestIedsDbOperations):

    def setUp(self):
        """Set up test fixtures"""
        # Reset global table variable for each test
        ieds_db_operations.ieds_table = None

        # Mock get_delta_table
        self.get_delta_table_patcher = patch('ieds_db_operations.get_delta_table')
        self.mock_get_delta_table = self.get_delta_table_patcher.start()

        # Create mock table
        self.mock_table = MagicMock()
        self.mock_get_delta_table.return_value = self.mock_table

        # Mock get_ieds_table
        self.get_ieds_table_patcher = patch('ieds_db_operations.get_ieds_table')
        self.mock_get_ieds_table = self.get_ieds_table_patcher.start()
        self.mock_get_ieds_table.return_value = self.mock_table

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()

    """Test ieds_check_exist function"""
    def test_ieds_check_exist_record_exists(self):
        """Test when record exists in IEDS table"""
        # Arrange
        patient_id = "test-patient-123"
        mock_response = {
            'Items': [{'PK': 'Patient#test-patient-123', 'SK': 'RECORD#1'}],
            'Count': 1
        }
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertTrue(result)

        self.mock_table.query.assert_called_once()

    def test_ieds_check_exist_record_not_exists(self):
        """Test when no record exists in IEDS table"""
        # Arrange
        patient_id = "test-patient-456"
        mock_response = {
            'Items': [],
            'Count': 0
        }
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify query parameters
        expected_pk = f"Patient#{patient_id}"
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq(expected_pk),
            Limit=1
        )

    def test_ieds_check_exist_empty_id(self):
        """Test with empty patient ID"""
        # Arrange
        patient_id = ""
        mock_response = {'Items': [], 'Count': 0}
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify query with empty ID
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq("Patient#"),
            Limit=1
        )

    def test_ieds_check_exist_none_id(self):
        """Test with None patient ID"""
        # Arrange
        patient_id = None
        mock_response = {'Items': [], 'Count': 0}
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify query with None ID
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq("Patient#None"),
            Limit=1
        )

    def test_ieds_check_exist_query_exception(self):
        """Test exception handling during query"""
        # Arrange
        patient_id = "test-patient-error"
        self.mock_table.query.side_effect = Exception("DynamoDB query failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_check_exist(patient_id)

        self.assertEqual(str(context.exception), "DynamoDB query failed")

        # Verify query was attempted
        self.mock_table.query.assert_called_once()

    def test_ieds_check_exist_missing_count_field(self):
        """Test when response doesn't have Count field"""
        # Arrange
        patient_id = "test-patient-no-count"
        mock_response = {'Items': []}  # Missing Count field
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)  # Should default to 0 when Count is missing

    def test_ieds_check_exist_count_greater_than_one(self):
        """Test when Count is greater than 1 (should still return True)"""
        # Arrange
        patient_id = "test-patient-multiple"
        mock_response = {
            'Items': [
                {'PK': 'Patient#test-patient-multiple', 'SK': 'RECORD#1'},
                {'PK': 'Patient#test-patient-multiple', 'SK': 'RECORD#2'}
            ],
            'Count': 2  # Even though Limit=1, Count could theoretically be higher
        }
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertTrue(result)


class TestUpdatePatientIdInIEDS(TestIedsDbOperations):
    """Test ieds_update_patient_id function"""

    def test_ieds_update_patient_id_success(self):
        """Test successful patient ID update"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        mock_update_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        self.mock_table.update_item.return_value = mock_update_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "success",
            "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify update_item was called correctly
        self.mock_table.update_item.assert_called_once()

        # Verify table was retrieved
        self.mock_get_delta_table.assert_called_once_with('test-ieds-table')

    def test_ieds_update_patient_id_empty_old_id(self):
        """Test update with empty old_id"""
        # Arrange
        old_id = ""
        new_id = "new-patient-456"

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()
        self.mock_get_delta_table.assert_not_called()

    def test_ieds_update_patient_id_empty_new_id(self):
        """Test update with empty new_id"""
        # Arrange
        old_id = "old-patient-123"
        new_id = ""

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_ieds_update_patient_id_both_ids_empty(self):
        """Test update with both IDs empty"""
        # Arrange
        old_id = ""
        new_id = ""

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_ieds_update_patient_id_none_old_id(self):
        """Test update with None old_id"""
        # Arrange
        old_id = None
        new_id = "new-patient-456"

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_ieds_update_patient_id_none_new_id(self):
        """Test update with None new_id"""
        # Arrange
        old_id = "old-patient-123"
        new_id = None

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_ieds_update_patient_id_whitespace_ids(self):
        """Test update with whitespace-only IDs"""
        # Arrange
        old_id = "   "
        new_id = "\t\n"

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        # Note: Current implementation checks "not old_id" which evaluates to False for whitespace
        # This test documents current behavior - you might want to add .strip() validation
        expected_result = {"status": "error", "message": "Old ID and New ID cannot be empty"}
        self.assertEqual(result, expected_result)

        # Verify update was called with whitespace IDs
        self.mock_table.update_item.assert_not_called()

    def test_ieds_update_patient_id_update_exception(self):
        """Test exception handling during update_item"""
        # Arrange
        old_id = "old-patient-error"
        nhs_number = "new-patient-error"
        self.mock_table.update_item.side_effect = Exception("DynamoDB update failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_update_patient_id(old_id, nhs_number)

        # Verify update was attempted
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{nhs_number}"}
        )
        # check logger exception was called
        self.mock_logger.exception.assert_called_once()
        self.assertEqual(str(context.exception), "DynamoDB update failed")

    def test_ieds_update_patient_id_same_old_and_new_id(self):
        """Test update when old_id and new_id are the same"""
        # Arrange
        id = "same-patient-id"

        # Act
        result = ieds_db_operations.ieds_update_patient_id(id, id)

        # Assert
        expected_result = {"status": "success", "message": f"No change in patient ID: {id}"}
        self.assertEqual(result, expected_result)

        self.mock_table.update_item.assert_not_called()
