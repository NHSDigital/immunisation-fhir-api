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


class TestCheckRecordExistInIEDS(TestIedsDbOperations):
    """Test check_record_exist_in_IEDS function"""

    def test_check_record_exist_in_ieds_record_exists(self):
        """Test when record exists in IEDS table"""
        # Arrange
        patient_id = "test-patient-123"
        mock_response = {
            'Items': [{'PK': 'Patient#test-patient-123', 'SK': 'RECORD#1'}],
            'Count': 1
        }
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Assert
        self.assertTrue(result)

        # Verify query parameters
        expected_pk = f"Patient#{patient_id}"
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq(expected_pk),
            Limit=1
        )

        # Verify table was retrieved
        self.mock_get_delta_table.assert_called_once_with('test-ieds-table')

    def test_check_record_exist_in_ieds_record_not_exists(self):
        """Test when no record exists in IEDS table"""
        # Arrange
        patient_id = "test-patient-456"
        mock_response = {
            'Items': [],
            'Count': 0
        }
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify query parameters
        expected_pk = f"Patient#{patient_id}"
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq(expected_pk),
            Limit=1
        )

    def test_check_record_exist_in_ieds_empty_id(self):
        """Test with empty patient ID"""
        # Arrange
        patient_id = ""
        mock_response = {'Items': [], 'Count': 0}
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify query with empty ID
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq("Patient#"),
            Limit=1
        )

    def test_check_record_exist_in_ieds_none_id(self):
        """Test with None patient ID"""
        # Arrange
        patient_id = None
        mock_response = {'Items': [], 'Count': 0}
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Assert
        self.assertFalse(result)

        # Verify query with None ID
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq("Patient#None"),
            Limit=1
        )

    def test_check_record_exist_in_ieds_query_exception(self):
        """Test exception handling during query"""
        # Arrange
        patient_id = "test-patient-error"
        self.mock_table.query.side_effect = Exception("DynamoDB query failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        self.assertEqual(str(context.exception), "DynamoDB query failed")

        # Verify query was attempted
        expected_pk = f"Patient#{patient_id}"
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq(expected_pk),
            Limit=1
        )

    def test_check_record_exist_in_ieds_missing_count_field(self):
        """Test when response doesn't have Count field"""
        # Arrange
        patient_id = "test-patient-no-count"
        mock_response = {'Items': []}  # Missing Count field
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Assert
        self.assertFalse(result)  # Should default to 0 when Count is missing

    def test_check_record_exist_in_ieds_count_greater_than_one(self):
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
        result = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Assert
        self.assertTrue(result)


class TestUpdatePatientIdInIEDS(TestIedsDbOperations):
    """Test update_patient_id_in_IEDS function"""

    def test_update_patient_id_in_ieds_success(self):
        """Test successful patient ID update"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

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
        self.mock_get_delta_table.assert_called_once_with('test-ieds-table')

    def test_update_patient_id_in_ieds_empty_old_id(self):
        """Test update with empty old_id"""
        # Arrange
        old_id = ""
        new_id = "new-patient-456"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()
        self.mock_get_delta_table.assert_not_called()

    def test_update_patient_id_in_ieds_empty_new_id(self):
        """Test update with empty new_id"""
        # Arrange
        old_id = "old-patient-123"
        new_id = ""

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_update_patient_id_in_ieds_both_ids_empty(self):
        """Test update with both IDs empty"""
        # Arrange
        old_id = ""
        new_id = ""

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_update_patient_id_in_ieds_none_old_id(self):
        """Test update with None old_id"""
        # Arrange
        old_id = None
        new_id = "new-patient-456"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_update_patient_id_in_ieds_none_new_id(self):
        """Test update with None new_id"""
        # Arrange
        old_id = "old-patient-123"
        new_id = None

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Old ID and New ID cannot be empty"
        }
        self.assertEqual(result, expected_result)

        # Verify no update was attempted
        self.mock_table.update_item.assert_not_called()

    def test_update_patient_id_in_ieds_whitespace_ids(self):
        """Test update with whitespace-only IDs"""
        # Arrange
        old_id = "   "
        new_id = "\t\n"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        # Note: Current implementation checks "not old_id" which evaluates to False for whitespace
        # This test documents current behavior - you might want to add .strip() validation
        expected_result = {
            "status": "success",
            "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify update was called with whitespace IDs
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

    def test_update_patient_id_in_ieds_update_exception(self):
        """Test exception handling during update_item"""
        # Arrange
        old_id = "old-patient-error"
        new_id = "new-patient-error"
        self.mock_table.update_item.side_effect = Exception("DynamoDB update failed")

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        self.assertEqual(str(context.exception), "DynamoDB update failed")

        # Verify update was attempted
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

    def test_update_patient_id_in_ieds_special_characters(self):
        """Test update with special characters in IDs"""
        # Arrange
        old_id = "patient-with-special@chars#123"
        new_id = "new-patient!@#$%^&*()"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "success",
            "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify update handles special characters correctly
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

    def test_update_patient_id_in_ieds_same_old_and_new_id(self):
        """Test update when old_id and new_id are the same"""
        # Arrange
        old_id = "same-patient-id"
        new_id = "same-patient-id"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        expected_result = {
            "status": "success",
            "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"
        }
        self.assertEqual(result, expected_result)

        # Verify update was still called (no optimization to skip same IDs)
        self.mock_table.update_item.assert_called_once()


class TestIedsDbOperationsIntegration(TestIedsDbOperations):
    """Integration tests for IEDS database operations"""

    def test_check_and_update_workflow(self):
        """Test typical workflow: check if record exists, then update"""
        # Arrange
        patient_id = "workflow-test-patient"
        old_id = "old-workflow-id"
        new_id = "new-workflow-id"

        # Mock check operation
        check_response = {'Items': [{'PK': f'Patient#{patient_id}'}], 'Count': 1}
        self.mock_table.query.return_value = check_response

        # Act - Check if record exists
        exists = ieds_db_operations.check_record_exist_in_IEDS(patient_id)

        # Act - Update patient ID if exists
        if exists:
            update_result = ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        self.assertTrue(exists)
        self.assertEqual(update_result["status"], "success")

        # Verify both operations were called
        self.mock_table.query.assert_called_once()
        self.mock_table.update_item.assert_called_once()

    def test_global_table_sharing_between_functions(self):
        """Test that both functions use the same cached table instance"""
        # Arrange
        patient_id = "shared-table-test"
        old_id = "old-shared-id"
        new_id = "new-shared-id"

        # Mock responses
        self.mock_table.query.return_value = {'Count': 1}

        # Act - Call both functions
        ieds_db_operations.check_record_exist_in_IEDS(patient_id)
        ieds_db_operations.update_patient_id_in_IEDS(old_id, new_id)

        # Assert
        # Should only initialize table once despite two function calls
        self.mock_get_delta_table.assert_called_once_with('test-ieds-table')

        # Both operations should use the same table instance
        self.mock_table.query.assert_called_once()
        self.mock_table.update_item.assert_called_once()


class TestEdgeCasesAndErrorHandling(TestIedsDbOperations):
    """Test edge cases and error scenarios"""

    def test_very_long_patient_ids(self):
        """Test with very long patient IDs"""
        # Arrange
        long_id = "a" * 1000  # Very long ID
        mock_response = {'Count': 0}
        self.mock_table.query.return_value = mock_response

        # Act
        result = ieds_db_operations.check_record_exist_in_IEDS(long_id)

        # Assert
        self.assertFalse(result)

        # Verify long ID was handled correctly
        expected_pk = f"Patient#{long_id}"
        self.mock_table.query.assert_called_once_with(
            KeyConditionExpression=Key("PK").eq(expected_pk),
            Limit=1
        )

    def test_unicode_patient_ids(self):
        """Test with Unicode characters in patient IDs"""
        # Arrange
        unicode_old_id = "患者-测试-123"
        unicode_new_id = "пациент-тест-456"

        # Act
        result = ieds_db_operations.update_patient_id_in_IEDS(unicode_old_id, unicode_new_id)

        # Assert
        self.assertEqual(result["status"], "success")

        # Verify Unicode IDs were handled correctly
        self.mock_table.update_item.assert_called_once_with(
            Key={"PK": f"Patient#{unicode_old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{unicode_new_id}"}
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
