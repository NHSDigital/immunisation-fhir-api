import unittest
from unittest.mock import MagicMock, patch

import ieds_db_operations
from exceptions.id_sync_exception import IdSyncException
from ieds_db_operations import extract_patient_resource_from_item


class TestExtractPatientResourceFromItem(unittest.TestCase):
    def test_extract_from_dict_with_contained_patient(self):
        item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [{"resourceType": "Patient", "id": "P1", "name": [{"family": "Doe"}]}],
            }
        }

        patient = extract_patient_resource_from_item(item)
        self.assertIsNotNone(patient)
        self.assertIsInstance(patient, dict)
        self.assertEqual(patient.get("resourceType"), "Patient")
        self.assertEqual(patient.get("id"), "P1")

    def test_extract_from_json_string(self):
        resource_json = '{"resourceType": "Immunization", "contained": [{"resourceType": "Patient", "id": "P2"}]}'
        item = {"Resource": resource_json}

        patient = extract_patient_resource_from_item(item)
        self.assertIsNotNone(patient)
        self.assertEqual(patient.get("id"), "P2")

    def test_malformed_json_string_returns_none(self):
        # A malformed JSON string should not raise, but return None
        item = {"Resource": "{not: valid json}"}
        self.assertIsNone(extract_patient_resource_from_item(item))

    def test_non_dict_resource_returns_none(self):
        item = {"Resource": 12345}
        self.assertIsNone(extract_patient_resource_from_item(item))

    def test_missing_resource_returns_none(self):
        item = {}
        self.assertIsNone(extract_patient_resource_from_item(item))


class TestIedsDbOperations(unittest.TestCase):
    """Base test class for IEDS database operations"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset global table variable for each test
        ieds_db_operations.ieds_table = None

        # Mock get_ieds_table_name
        self.get_ieds_table_name_patcher = patch("ieds_db_operations.get_ieds_table_name")
        self.mock_get_ieds_table_name = self.get_ieds_table_name_patcher.start()
        self.mock_get_ieds_table_name.return_value = "test-ieds-table"

        # mock logger.exception
        self.logger_patcher = patch("ieds_db_operations.logger")
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        """Clean up patches"""
        patch.stopall()


class TestGetIedsTable(TestIedsDbOperations):
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Mock get_dynamodb_table function
        self.get_dynamodb_table_patcher = patch("ieds_db_operations.get_dynamodb_table")
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
        table_name = "test-ieds-table"
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
        table_name = "test-ieds-table"
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
        table_name = "test-ieds-table"
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
        table_name = "test-ieds-table"
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
        table_name1 = "test-ieds-table-1"
        self.mock_get_ieds_table_name.return_value = table_name1

        # Act - First call
        result1 = ieds_db_operations.get_ieds_table()

        # Reset global variable and change table name
        ieds_db_operations.ieds_table = None
        table_name2 = "test-ieds-table-2"
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
            unittest.mock.call(table_name2),
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
        table_name = "test-ieds-table"
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
        self.mock_get_ieds_table = patch("ieds_db_operations.get_ieds_table")
        self.mock_get_ieds_table_patcher = self.mock_get_ieds_table.start()
        self.mock_table = MagicMock()
        self.mock_get_ieds_table_patcher.return_value = self.mock_table

        self.mock_dynamodb_client = patch("ieds_db_operations.dynamodb_client")
        self.mock_dynamodb_client_patcher = self.mock_dynamodb_client.start()

        # Mock transact_write_items (not update_item)
        self.mock_dynamodb_client_patcher.transact_write_items = MagicMock()

        # Mock get_items_from_patient_id
        self.get_items_from_patient_id_patcher = patch("ieds_db_operations.get_items_from_patient_id")
        self.mock_get_items_from_patient_id = self.get_items_from_patient_id_patcher.start()

        # Mock get_ieds_table_name
        self.get_ieds_table_name_patcher = patch("ieds_db_operations.get_ieds_table_name")
        self.mock_get_ieds_table_name_mock = self.get_ieds_table_name_patcher.start()
        self.mock_get_ieds_table_name_mock.return_value = "test-ieds-table"

    def test_ieds_update_patient_id_success(self):
        """Test successful patient ID update"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Mock items to update
        mock_items = [
            {"PK": "Immunization#old-patient-123", "PatientPK": "Patient#old-patient-123"},
            {"PK": "Patient#old-patient-123#record1", "PatientPK": "Patient#old-patient-123"},
        ]

        # Mock successful transact_write_items response
        mock_transact_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        self.mock_dynamodb_client_patcher.transact_write_items.return_value = mock_transact_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id, mock_items)

        # Assert - Update expected message to match actual implementation
        expected_result = {
            "status": "success",
            "message": f"IEDS update. {len(mock_items)} item(s) updated in 1 batch(es).",
        }
        self.assertEqual(result, expected_result)

        # Verify transact_write_items was called
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()

    def test_ieds_update_patient_id_non_200_response(self):
        """Test update with non-200 HTTP status code"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Mock items to update
        mock_items = [{"PK": "Patient#old-patient-123", "PatientPK": "Patient#old-patient-123"}]

        # Mock failed transact_write_items response (not update_item)
        mock_transact_response = {"ResponseMetadata": {"HTTPStatusCode": 400}}
        self.mock_dynamodb_client_patcher.transact_write_items.return_value = mock_transact_response

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id, mock_items)

        # Assert
        expected_result = {
            "status": "error",
            "message": "Failed to update some batches for patient ID",
        }
        self.assertEqual(result, expected_result)

        # Verify transact_write_items was called (not update_item)
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()

    def test_ieds_update_patient_id_no_items_found(self):
        """Test when no items are found to update"""
        # Arrange
        old_id = "old-patient-123"
        new_id = "new-patient-456"

        # Act
        result = ieds_db_operations.ieds_update_patient_id(old_id, new_id, [])

        # Assert
        expected_result = {
            "status": "success",
            "message": "No items found to update for patient ID",
        }
        self.assertEqual(result, expected_result)

        # Verify no transact operation was attempted
        self.mock_table.transact_write_items.assert_not_called()

    def test_ieds_update_patient_id_update_exception(self):
        """Test exception handling during transact_write_items"""
        # Arrange
        old_id = "old-patient-error"
        new_id = "new-patient-error"

        # Mock items to update
        mock_items = [
            {
                "PK": "Patient#old-patient-error",
                "PatientPK": "Patient#old-patient-error",
            }
        ]

        test_exception = Exception("DynamoDB transact failed")
        self.mock_dynamodb_client_patcher.transact_write_items.side_effect = test_exception

        # Act & Assert
        with self.assertRaises(Exception) as context:
            ieds_db_operations.ieds_update_patient_id(old_id, new_id, mock_items)

        exception = context.exception
        self.assertIsInstance(exception, IdSyncException)
        self.assertEqual(exception.message, "Error updating patient ID")

        # Verify transact was attempted
        self.mock_dynamodb_client_patcher.transact_write_items.assert_called_once()

        # Verify logger exception was called
        self.mock_logger.exception.assert_called_once_with("Error updating patient ID")


class TestGetItemsToUpdate(TestIedsDbOperations):
    def setUp(self):
        super().setUp()
        # Mock get_ieds_table()
        self.mock_get_ieds_table = patch("ieds_db_operations.get_ieds_table")
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
            {"PK": f"Patient#{patient_id}", "PatientPK": f"Patient#{patient_id}"},
            {
                "PK": f"Patient#{patient_id}#record1",
                "PatientPK": f"Patient#{patient_id}",
            },
        ]
        self.mock_table.query.return_value = {
            "Items": expected_items,
            "Count": len(expected_items),
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
        self.mock_table.query.return_value = {"Items": [], "Count": 0}

        # Act
        result = ieds_db_operations.get_items_from_patient_id(patient_id)

        # Assert
        self.assertEqual(result, [])


class TestIedsDbOperationsConditional(unittest.TestCase):
    def setUp(self):
        # Patch logger to suppress output
        self.logger_patcher = patch("ieds_db_operations.logger")
        self.mock_logger = self.logger_patcher.start()

        # Patch get_ieds_table_name and get_ieds_table
        self.get_ieds_table_name_patcher = patch("ieds_db_operations.get_ieds_table_name")
        self.mock_get_ieds_table_name = self.get_ieds_table_name_patcher.start()
        self.mock_get_ieds_table_name.return_value = "test-table"

        self.get_ieds_table_patcher = patch("ieds_db_operations.get_ieds_table")
        self.mock_get_ieds_table = self.get_ieds_table_patcher.start()

        # Patch dynamodb client
        self.dynamodb_client_patcher = patch("ieds_db_operations.dynamodb_client")
        self.mock_dynamodb_client = self.dynamodb_client_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_ieds_update_with_items_to_update_uses_provided_list(self):
        items = [{"PK": "Patient#1"}, {"PK": "Patient#1#r2"}]
        # patch transact_write_items to return success
        self.mock_dynamodb_client.transact_write_items = MagicMock(
            return_value={"ResponseMetadata": {"HTTPStatusCode": 200}}
        )

        res = ieds_db_operations.ieds_update_patient_id("1", "2", items_to_update=items)
        self.assertEqual(res["status"], "success")
        # ensure transact called at least once
        self.mock_dynamodb_client.transact_write_items.assert_called()

    def test_ieds_update_batches_multiple_calls(self):
        # create 60 items to force 3 batches (25,25,10)
        items = [{"PK": f"Patient#old#{i}"} for i in range(60)]
        called = []

        def fake_transact(TransactItems):
            called.append(len(TransactItems))
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

        self.mock_dynamodb_client.transact_write_items = MagicMock(side_effect=fake_transact)

        res = ieds_db_operations.ieds_update_patient_id("old", "new", items_to_update=items)
        self.assertEqual(res["status"], "success")
        # should have been called 3 times
        self.assertEqual(len(called), 3)
        self.assertEqual(called[0], 25)
        self.assertEqual(called[1], 25)
        self.assertEqual(called[2], 10)

    def test_ieds_update_non_200_response(self):
        items = [{"PK": "Patient#1"}]
        self.mock_dynamodb_client.transact_write_items = MagicMock(
            return_value={"ResponseMetadata": {"HTTPStatusCode": 500}}
        )

        res = ieds_db_operations.ieds_update_patient_id("1", "2", items_to_update=items)
        self.assertEqual(res["status"], "error")
