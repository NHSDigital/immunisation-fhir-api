import unittest
from unittest.mock import patch, MagicMock
from exceptions.id_sync_exception import IdSyncException

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
        # Use the correct mock that exists in this test class
        self.mock_get_dynamodb_table.side_effect = Exception("Table initialization failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.get_ieds_table()

        self.assertEqual(str(context.exception), "Table initialization failed")

        # Verify global variable remains None after failure
        self.assertIsNone(ieds_db_operations.ieds_table)

        # Verify the correct mocks were called
        self.mock_get_ieds_table_name.assert_called_once()
        self.mock_get_dynamodb_table.assert_called_once()


class TestUpdatePatientIdInIEDS(TestIedsDbOperations):

    def setUp(self):
        super().setUp()
        # Mock get_ieds_table() and subsequent calls
        self.mock_get_ieds_table = patch('ieds_db_operations.get_ieds_table')
        self.mock_get_ieds_table_patcher = self.mock_get_ieds_table.start()
        self.mock_table = MagicMock()
        self.mock_get_ieds_table_patcher.return_value = self.mock_table

        self.mock_dynamodb_client = patch('ieds_db_operations.dynamodb_client')
        self.mock_dynamodb_client_patcher = self.mock_dynamodb_client.start()

        # Mock transact_write_items (not update_item)
        self.mock_dynamodb_client_patcher.transact_write_items = MagicMock()

        # Mock get_items_from_patient_id
        self.get_items_from_patient_id_patcher = patch('ieds_db_operations.get_items_from_patient_id')
        self.mock_get_items_from_patient_id = self.get_items_from_patient_id_patcher.start()

        # Mock get_ieds_table_name
        self.get_ieds_table_name_patcher = patch('ieds_db_operations.get_ieds_table_name')
        self.mock_get_ieds_table_name_mock = self.get_ieds_table_name_patcher.start()
        self.mock_get_ieds_table_name_mock.return_value = 'test-ieds-table'

    def test_ieds_update_patient_id_success(self):
        """Test successful patient ID update"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Mock items to update
        mock_items = [
            {'PK': 'Patient#old-patient-123', 'PatientPK': 'Patient#old-patient-123'},
            {'PK': 'Patient#old-patient-123#record1', 'PatientPK': 'Patient#old-patient-123'}
        ]
        self.mock_get_items_from_patient_id.return_value = mock_items

        # Mock successful transact_write_items response
        mock_transact_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        self.mock_dynamodb_client_patcher.transact_write_items.return_value = mock_transact_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert - Update expected message to match actual implementation
        expected_result = {
            "status": "success",
            "message": f"IEDS update, patient ID: {old_id}=>{new_id}. {len(mock_items)} updated 1."
        }
        self.assertEqual(result, expected_result)

        # Verify get_items_from_patient_id was called
        self.mock_get_items_from_patient_id.assert_called_once_with(old_id)

        # Verify transact_write_items was called
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()

    def test_ieds_update_patient_id_non_200_response(self):
        """Test update with non-200 HTTP status code"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Mock items to update
        mock_items = [{'PK': 'Patient#old-patient-123', 'PatientPK': 'Patient#old-patient-123'}]
        self.mock_get_items_from_patient_id.return_value = mock_items

        # Mock failed transact_write_items response (not update_item)
        mock_transact_response = {'ResponseMetadata': {'HTTPStatusCode': 400}}
        self.mock_dynamodb_client_patcher.transact_write_items.return_value = mock_transact_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": f"Failed to update some batches for patient ID: {old_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify transact_write_items was called (not update_item)
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()

    def test_ieds_update_patient_id_no_items_found(self):
        """Test when no items are found to update"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Mock empty items list
        self.mock_get_items_from_patient_id.return_value = []

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        expected_result = {
            "status": "success",
            "message": f"No items found to update for patient ID: {old_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify get_items_from_patient_id was called
        self.mock_get_items_from_patient_id.assert_called_once_with(old_id)

        # Verify no transact operation was attempted
        self.mock_table.transact_write_items.assert_not_called()

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
        self.mock_table.transact_write_items.assert_not_called()
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
        self.mock_table.transact_write_items.assert_not_called()
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
        self.mock_table.transact_write_items.assert_not_called()
        self.mock_get_ieds_table_patcher.assert_not_called()

    def test_ieds_update_patient_id_update_exception(self):
        """Test exception handling during transact_write_items"""
        # Arrange
        old_id = "old-patient-error"
        new_id = "new-patient-error"

        # Mock items to update
        mock_items = [{'PK': 'Patient#old-patient-error', 'PatientPK': 'Patient#old-patient-error'}]
        self.mock_get_items_from_patient_id.return_value = mock_items

        test_exception = Exception("DynamoDB transact failed")
        self.mock_dynamodb_client_patcher.transact_write_items.side_effect = test_exception

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        exception = context.exception
        self.assertIsInstance(exception, IdSyncException)
        self.assertEqual(exception.message, f"Error updating patient Id from :{old_id} to {new_id}")
        self.assertEqual(exception.nhs_numbers, [old_id, new_id])
        self.assertEqual(exception.inner_exception, test_exception)

        # Verify transact was attempted
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()

        # Verify logger exception was called
        self.mock_logger.exception.assert_called_once_with("Error updating patient ID")

    def test_ieds_update_patient_id_special_characters(self):
        """Test update with special characters in IDs"""
        # Arrange
        old_id = "old-patient@123#$%"
        new_id = "new-patient&456*()+"

        # Mock items to update
        mock_items = [{'PK': f'Patient#{old_id}', 'PatientPK': f'Patient#{old_id}'}]
        self.mock_get_items_from_patient_id.return_value = mock_items

        mock_transact_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        self.mock_dynamodb_client_patcher.transact_write_items.return_value = mock_transact_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id)

        # Assert
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], f"IEDS update, patient ID: {old_id}=>{new_id}. {len(mock_items)} updated 1.")

        # Verify transact_write_items was called with special characters
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()


class TestGetItemsToUpdate(TestIedsDbOperations):

    def setUp(self):
        super().setUp()
        # Mock get_ieds_table()
        self.mock_get_ieds_table = patch('ieds_db_operations.get_ieds_table')
        self.mock_get_ieds_table_patcher = self.mock_get_ieds_table.start()
        self.mock_table = MagicMock()
        self.mock_get_ieds_table_patcher.return_value = self.mock_table

    def tearDown(self):
        patch.stopall()

    def test_get_items_from_patient_id_success(self):
        """Test successful retrieval of items to update"""
        # Arrange
        patient_id = "test-patient-123"
        expected_items = [
            {'PK': f'Patient#{patient_id}', 'PatientPK': f'Patient#{patient_id}'},
            {'PK': f'Patient#{patient_id}#record1', 'PatientPK': f'Patient#{patient_id}'}
        ]
        self.mock_table.query.return_value = {
            'Items': expected_items,
            'Count': len(expected_items)
        }

        # Act
        result = ieds_db_operations.get_items_from_patient_id(patient_id)

        # Assert
        self.assertEqual(result, expected_items)

        # Verify query was called with correct parameters
        self.mock_table.query.assert_called_once()

    def test_get_items_from_patient_id_no_records(self):
        """Test when no records are found for the patient ID"""
        # Arrange
        patient_id = "test-patient-no-records"
        self.mock_table.query.return_value = {
            'Items': [],
            'Count': 0
        }

        # Act
        result = ieds_db_operations.get_items_from_patient_id(patient_id)

        # Assert
        self.assertEqual(result, [])


class TestIedsCheckExists(TestIedsDbOperations):

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Mock get_items_from_patient_id instead of table.query
        self.get_items_from_patient_id_patcher = patch('ieds_db_operations.get_items_from_patient_id')
        self.mock_get_items_from_patient_id = self.get_items_from_patient_id_patcher.start()

    def tearDown(self):
        """Clean up patches"""
        super().tearDown()

    def test_ieds_check_exist_record_exists(self):
        """Test when record exists in IEDS table"""
        # Arrange
        patient_id = "test-patient-123"
        mock_items = [{'PK': 'Patient#test-patient-123', 'PatientPK': 'Patient#test-patient-123'}]
        self.mock_get_items_from_patient_id.return_value = mock_items

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertTrue(result)

        # Verify get_items_from_patient_id was called with correct parameters
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_record_not_exists(self):
        """Test when no record exists in IEDS table"""
        # Arrange
        patient_id = "test-patient-456"
        self.mock_get_items_from_patient_id.return_value = []

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify get_items_from_patient_id was called
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_empty_id(self):
        """Test with empty patient ID"""
        # Arrange
        patient_id = ""
        self.mock_get_items_from_patient_id.return_value = []

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify get_items_from_patient_id was called with empty ID
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_none_id(self):
        """Test with None patient ID"""
        # Arrange
        patient_id = None
        self.mock_get_items_from_patient_id.return_value = []

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify get_items_from_patient_id was called with None ID
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_query_exception(self):
        """Test exception handling during get_items_from_patient_id"""
        # Arrange
        patient_id = "test-patient-error"
        test_exception = Exception("DynamoDB query failed")
        self.mock_get_items_from_patient_id.side_effect = test_exception

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_check_exist(patient_id)

        self.assertEqual(str(context.exception), "DynamoDB query failed")

        # Verify get_items_from_patient_id was attempted
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_multiple_items_found(self):
        """Test when multiple items are found (should still return True)"""
        # Arrange
        patient_id = "test-patient-multiple"
        mock_items = [
            {'PK': 'Patient#test-patient-multiple', 'PatientPK': 'Patient#test-patient-multiple'},
            {'PK': 'Patient#test-patient-multiple#record1', 'PatientPK': 'Patient#test-patient-multiple'}
        ]
        self.mock_get_items_from_patient_id.return_value = mock_items

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertTrue(result)

        # Verify get_items_from_patient_id was called with limit=1
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_single_item_found(self):
        """Test when exactly one item is found"""
        # Arrange
        patient_id = "test-patient-single"
        mock_items = [{'PK': 'Patient#test-patient-single', 'PatientPK': 'Patient#test-patient-single'}]
        self.mock_get_items_from_patient_id.return_value = mock_items

        # Act
        result = ieds_db_operations.ieds_check_exist(patient_id)

        # Assert
        self.assertTrue(result)

        # Verify get_items_from_patient_id was called
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    def test_ieds_check_exist_limit_parameter(self):
        """Test that the function passes limit=1 to get_items_from_patient_id"""
        # Arrange
        patient_id = "test-patient-limit"
        self.mock_get_items_from_patient_id.return_value = []

        # Act
        ieds_db_operations.ieds_check_exist(patient_id)

        # Assert - Verify the limit parameter is correctly passed
        self.mock_get_items_from_patient_id.assert_called_once_with(patient_id, 1)

    # ✅ Remove tests that are no longer relevant:
    # - test_ieds_check_exist_missing_count_field (no longer uses Count)
    # - test_ieds_check_exist_count_greater_than_one (no longer uses Count)
