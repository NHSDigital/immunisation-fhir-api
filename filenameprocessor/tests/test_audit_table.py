"""Tests for audit_table functions"""

from unittest import TestCase
from unittest.mock import patch
from boto3 import resource as boto3_resource
from moto import mock_dynamodb

from audit_table import add_to_audit_table
from errors import DuplicateFileError, UnhandledAuditTableError
from clients import REGION_NAME
from tests.utils_for_tests.values_for_tests import MOCK_ENVIRONMENT_DICT


@mock_dynamodb
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestAuditTable(TestCase):
    """Tests for audit table functions"""

    def setUp(self):
        """Set up test values to be used for the tests"""
        self.dynamodb_resource = boto3_resource("dynamodb", region_name=REGION_NAME)
        self.audit_table_name = MOCK_ENVIRONMENT_DICT["AUDIT_TABLE_NAME"]

        self.table = self.dynamodb_resource.create_table(
            TableName=self.audit_table_name,
            KeySchema=[{"AttributeName": "message_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "message_id", "AttributeType": "S"},
                {"AttributeName": "filename", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "filename_index",
                    "KeySchema": [{"AttributeName": "filename", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                }
            ],
        )

        assert self.table.table_status == "ACTIVE"
        assert len(self.table.global_secondary_indexes) == 1
        assert self.table.global_secondary_indexes[0]["IndexName"] == "filename_index"

    def test_add_to_audit_table(self):
        """Test that the add_to_audit_table function works as expected for the following:
        * Unique files: file is added to the audit table, no error is raised
        * Duplicate files (duplicated file name): file is added to the audit table, DuplicateFileError is raised
        * Overwrites (duplicated message_id): file is not added to the audit table, UnhandledAuditTableError is raised
        """
        message_id_1 = "test_id_1"
        message_id_2 = "test_id_2"
        message_id_3 = "test_id_3"
        file_key_1 = "test_file_1.csv"
        file_key_2 = "test_file_2.csv"
        file_key_4 = "test_file_4.csv"
        created_at_formatted_string_1 = "20240101T01000000"
        created_at_formatted_string_2 = "20240101T02000000"
        created_at_formatted_string_3 = "20240101T03000000"
        created_at_formatted_string_4 = "20240101T04000000"

        # Test case 1: file_key_1 should be added to the audit table
        expected_table_item_1 = {
            "message_id": message_id_1,
            "filename": file_key_1,
            "status": "Processed",
            "timestamp": created_at_formatted_string_1,
        }

        # Test case 2: file_key_2 should be added to the audit table
        expected_table_item_2 = {
            "message_id": message_id_2,
            "filename": file_key_2,
            "status": "Processed",
            "timestamp": created_at_formatted_string_2,
        }

        # Test case 3: file_key_1 should be added to the audit table again, even though the file name is a duplicate
        expected_table_item_3 = {
            "message_id": message_id_3,
            "filename": file_key_1,
            "status": "Processed",
            "timestamp": created_at_formatted_string_3,
        }

        # Test case 4: file_key_4 should not be added to the audit table because the message_id is a duplicate.
        # Note that this scenario should never occur as a new unique message_id is generated for each file upload,
        # even if the file name is a duplicate, but this test is included for safety because default behaviour of
        # dynamodb is to overwrite the existing item if the message_id is the same.
        expected_table_item_4 = {  # This item should not be added to the table
            "message_id": message_id_3,
            "filename": file_key_4,
            "status": "Processed",
            "timestamp": created_at_formatted_string_4,
        }

        # Add a file to the audit table
        self.assertIsNone(add_to_audit_table(message_id_1, file_key_1, created_at_formatted_string_1))
        table_items = self.table.scan()["Items"]
        assert len(table_items) == 1
        assert expected_table_item_1 in table_items

        # Add another file to the audit table
        self.assertIsNone(add_to_audit_table(message_id_2, file_key_2, created_at_formatted_string_2))
        table_items = self.table.scan()["Items"]
        assert len(table_items) == 2
        assert expected_table_item_1 in table_items
        assert expected_table_item_2 in table_items

        # Attempt to add the file 1 again - should raise a DuplicateFileError due to the file already being in the table
        with self.assertRaises(DuplicateFileError):
            add_to_audit_table(message_id_3, file_key_1, created_at_formatted_string_3)

        # Check that the file has been added to the audit table again,
        # with the different message_id and created_at_formatted_string
        table_items = self.table.scan()["Items"]
        assert len(table_items) == 3
        assert expected_table_item_1 in table_items
        assert expected_table_item_2 in table_items
        assert expected_table_item_3 in table_items

        # Attempt to add a file that is already in the table with the same message_id
        with self.assertRaises(UnhandledAuditTableError):
            add_to_audit_table(message_id_3, file_key_4, created_at_formatted_string_4)

        # Check that the file has not been added to the audit table
        table_items = self.table.scan()["Items"]
        assert len(table_items) == 3
        assert expected_table_item_1 in table_items
        assert expected_table_item_2 in table_items
        assert expected_table_item_3 in table_items
        assert expected_table_item_4 not in table_items
