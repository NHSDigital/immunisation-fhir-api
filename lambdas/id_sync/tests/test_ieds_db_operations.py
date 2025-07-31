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

        # mock logger.exception
        self.logger_patcher = patch('ieds_db_operations.logger')
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()


class TestGetIedsTable(TestIedsDbOperations):

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Mock get_dynamodb_table function
        self.get_dynamodb_table_patcher = patch('ieds_db_operations.get_dynamodb_table')
        self.mock_get_dynamodb_table = self.get_dynamodb_table_patcher.start()

        # Create mock table object
        self.mock_table = MagicMock()
        self.mock_get_dynamodb_table.return_value = self.mock_table

    def tearDown(self):
        """Clean up patches"""
        super().tearDown()

    """Test get_ieds_table function"""

    def test_get_ieds_table_first_call(self):
        """Test first call to get_ieds_table initializes the global variable"""
        # Arrange
        table_name = 'test-ieds-table'
        self.mock_get_ieds_table_name.return_value = table_name

        # Act
        result = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result, self.mock_table)
        self.assertEqual(ieds_db_operations.ieds_table, self.mock_table)

        # Verify function calls
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once_with(table_name)

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
        self.mock_get_dynamodb_table.assert_not_called()

    def test_get_ieds_table_exception_handling_get_table_name(self):
        """Test exception handling when get_ieds_table_name fails"""
        # Arrange
        self.mock_get_ieds_table_name.side_effect = Exception("Failed to get table name")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.get_ieds_table()

        self.assertEqual(str(context.exception), "Failed to get table name")

        # Verify global variable remains None after failure
        self.assertIsNone(ieds_db_operations.ieds_table)

        # Verify get_ieds_table_name was called but get_dynamodb_table was not
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_not_called()

    def test_get_ieds_table_exception_handling_get_dynamodb_table(self):
        """Test exception handling when get_dynamodb_table fails"""
        # Arrange
        table_name = 'test-ieds-table'
        self.mock_get_ieds_table_name.return_value = table_name
        self.mock_get_dynamodb_table.side_effect = Exception("Failed to get DynamoDB table")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.get_ieds_table()

        self.assertEqual(str(context.exception), "Failed to get DynamoDB table")

        # Verify global variable remains None after failure
        self.assertIsNone(ieds_db_operations.ieds_table)

        # Verify both functions were called
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once_with(table_name)

    def test_get_ieds_table_multiple_calls_same_session(self):
        """Test multiple calls in the same session use cached table"""
        # Arrange
        table_name = 'test-ieds-table'
        self.mock_get_ieds_table_name.return_value = table_name

        # Act - Make multiple calls
        result1 = ieds_db_operations.get_ieds_table()
        result2 = ieds_db_operations.get_ieds_table()
        result3 = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result1, self.mock_table)
        self.assertEqual(result2, self.mock_table)
        self.assertEqual(result3, self.mock_table)
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

        # Verify dependencies were called only once (first call)
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once_with(table_name)

    def test_get_ieds_table_reset_global_variable(self):
        """Test that resetting global variable forces re-initialization"""
        # Arrange - First call
        table_name = 'test-ieds-table'
        self.mock_get_ieds_table_name.return_value = table_name

        # Act - First call
        result1 = ieds_db_operations.get_ieds_table()

        # Reset global variable to simulate new Lambda execution
        ieds_db_operations.ieds_table = None

        # Act - Second call after reset
        result2 = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result1, self.mock_table)
        self.assertEqual(result2, self.mock_table)

        # Verify dependencies were called twice (once for each initialization)
        self.assertEqual(self.mock_get_ieds_table_name.call_count, 2)
        self.assertEqual(self.mock_get_dynamodb_table.call_count, 2)

    def test_get_ieds_table_with_different_table_names(self):
        """Test with different table names on different calls"""
        # Arrange - First call
        table_name1 = 'test-ieds-table-1'
        self.mock_get_ieds_table_name.return_value = table_name1

        # Act - First call
        result1 = ieds_db_operations.get_ieds_table()

        # Reset global variable and change table name
        ieds_db_operations.ieds_table = None
        table_name2 = 'test-ieds-table-2'
        self.mock_get_ieds_table_name.return_value = table_name2

        # Act - Second call with different table name
        result2 = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result1, self.mock_table)
        self.assertEqual(result2, self.mock_table)

        # Verify correct table names were used
        self.assertEqual(self.mock_get_ieds_table_name.call_count, 2)
        expected_calls = [
            unittest.mock.call(table_name1),
            unittest.mock.call(table_name2)
        ]
        self.mock_get_dynamodb_table.assert_has_calls(expected_calls)

    def test_get_ieds_table_empty_table_name(self):
        """Test when get_ieds_table_name returns empty string"""
        # Arrange
        self.mock_get_ieds_table_name.return_value = ""

        # Act
        result = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result, self.mock_table)
        self.assertEqual(ieds_db_operations.ieds_table, self.mock_table)

        # Verify empty string was passed to get_dynamodb_table
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once_with("")

    def test_get_ieds_table_none_table_name(self):
        """Test when get_ieds_table_name returns None"""
        # Arrange
        self.mock_get_ieds_table_name.return_value = None

        # Act
        result = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result, self.mock_table)
        self.assertEqual(ieds_db_operations.ieds_table, self.mock_table)

        # Verify None was passed to get_dynamodb_table
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once_with(None)

    def test_get_ieds_table_global_variable_consistency(self):
        """Test that global variable is consistently updated"""
        # Arrange
        table_name = 'test-ieds-table'
        self.mock_get_ieds_table_name.return_value = table_name

        # Verify initial state
        self.assertIsNone(ieds_db_operations.ieds_table)

        # Act
        result = ieds_db_operations.get_ieds_table()

        # Assert
        self.assertEqual(result, self.mock_table)
        self.assertIsNotNone(ieds_db_operations.ieds_table)
        self.assertEqual(ieds_db_operations.ieds_table, self.mock_table)
        self.assertEqual(ieds_db_operations.ieds_table, result)

    def test_get_ieds_table_exception_handling(self):
        """Test exception handling when table initialization fails"""
        # Arrange
        # ✅ Fix: Use the correct mock that exists in this test class
        self.mock_get_dynamodb_table.side_effect = Exception("Table initialization failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.get_ieds_table()

        self.assertEqual(str(context.exception), "Table initialization failed")

        # Verify global variable remains None after failure
        self.assertIsNone(ieds_db_operations.ieds_table)

        # ✅ Fix: Verify the correct mocks were called
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once()

class TestIedsCheckExists(TestIedsDbOperations):

    def setUp(self):
        """Set up test fixtures"""
        # Reset global table variable for each test
        ieds_db_operations.ieds_table = None

        # Mock get_ieds_table
        self.get_ieds_table_patcher = patch('ieds_db_operations.get_ieds_table')
        self.mock_get_ieds_table = self.get_ieds_table_patcher.start()

        # Create mock table
        self.mock_table = MagicMock()
        self.mock_get_ieds_table.return_value = self.mock_table

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

    def setUp(self):
        super().setUp()
        # Mock get_ieds_table() and subsequent call to update_item
        self.mock_get_ieds_table = patch('ieds_db_operations.get_ieds_table')
        self.mock_get_ieds_table_patcher = self.mock_get_ieds_table.start()
        self.mock_table = MagicMock()
        self.mock_get_ieds_table_patcher.return_value = self.mock_table
        # Mock update_item
        self.mock_table.update_item = MagicMock()

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
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

        # Verify table was retrieved
        self.mock_get_ieds_table_patcher.assert_called_once()

    def test_ieds_update_patient_id_non_200_response(self):
        """Test update with non-200 HTTP status code"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        mock_update_response = {'ResponseMetadata': {'HTTPStatusCode': 400}}
        self.mock_table.update_item.return_value = mock_update_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": f"Failed to update patient ID: {old_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify update_item was called
        self.mock_table.update_item.assert_called_once()

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
        self.mock_get_ieds_table_patcher.assert_not_called()

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
        self.mock_get_ieds_table_patcher.assert_not_called()

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
        self.mock_get_ieds_table_patcher.assert_not_called()

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
        self.mock_get_ieds_table_patcher.assert_not_called()

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
        self.mock_get_ieds_table_patcher.assert_not_called()

    def test_ieds_update_patient_id_whitespace_old_id(self):
        """Test update with whitespace-only old_id"""
        # Arrange
        old_id = "   "
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
        self.mock_get_ieds_table_patcher.assert_not_called()

    def test_ieds_update_patient_id_whitespace_new_id(self):
        """Test update with whitespace-only new_id"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "\t\n "

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
        self.mock_get_ieds_table_patcher.assert_not_called()

    def test_ieds_update_patient_id_both_ids_whitespace(self):
        """Test update with both IDs as whitespace-only"""
        # Arrange
        old_id = "   "
        new_id = "\t\n"

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
        self.mock_get_ieds_table_patcher.assert_not_called()

    def test_ieds_update_patient_id_same_old_and_new_id(self):
        """Test update when old_id and new_id are the same"""
        # Arrange
        patient_id = "same-patient-id"

        # Act
        result = ieds_db_operations.ieds_update_patient_id(patient_id, patient_id)

        # Assert
        expected_result = {
            "status": "success",
            "message": f"No change in patient ID: {patient_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()
        self.mock_get_ieds_table_patcher.assert_not_called()

    def test_ieds_update_patient_id_update_exception(self):
        """Test exception handling during update_item"""
        # Arrange
        old_id = "old-patient-error"
        new_id = "new-patient-error"
        self.mock_table.update_item.side_effect = Exception("DynamoDB update failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        self.assertEqual(str(context.exception), "DynamoDB update failed")

        # Verify update was attempted
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

        # Verify logger exception was called
        self.mock_logger.exception.assert_called_once_with("Error updating patient ID")

    def test_ieds_update_patient_id_get_table_exception(self):
        """Test exception handling when get_ieds_table fails"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"
        self.mock_get_ieds_table_patcher.side_effect = Exception("Failed to get IEDS table")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        self.assertEqual(str(context.exception), "Failed to get IEDS table")

        # Verify get_ieds_table was called
        self.mock_get_ieds_table_patcher.assert_called_once()

        # Verify update_item was not called since get_table failed
        self.mock_table.update_item.assert_not_called()

    def test_ieds_update_patient_id_missing_response_metadata(self):
        """Test when response doesn't have ResponseMetadata"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Mock response without ResponseMetadata - this would cause KeyError
        mock_update_response = {}
        self.mock_table.update_item.return_value = mock_update_response

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Verify update was attempted
        self.mock_table.update_item.assert_called_once()

        # Verify logger exception was called
        self.mock_logger.exception.assert_called_once_with("Error updating patient ID")

    def test_ieds_update_patient_id_special_characters(self):
        """Test update with special characters in IDs"""
        # Arrange
        old_id = "old-patient@123#$%"
        new_id = "new-patient&456*()+"

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

        # Verify update_item was called with special characters
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )
