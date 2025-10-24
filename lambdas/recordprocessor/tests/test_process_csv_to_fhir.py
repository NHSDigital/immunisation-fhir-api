"""Tests for process_csv_to_fhir function"""

import json
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

import boto3
from moto import mock_dynamodb, mock_firehose, mock_s3

from tests.utils_for_recordprocessor_tests.generic_setup_and_teardown import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
)
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    add_entry_to_table,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    REGION_NAME,
    MockFileDetails,
    ValidMockFileContent,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from batch_processor import process_csv_to_fhir
    from constants import AUDIT_TABLE_NAME, FileStatus

dynamodb_client = boto3.client("dynamodb", region_name=REGION_NAME)
s3_client = boto3.client("s3", region_name=REGION_NAME)
firehose_client = boto3.client("firehose", region_name=REGION_NAME)
test_file = MockFileDetails.rsv_emis


@mock_s3
@mock_firehose
@mock_dynamodb
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestProcessCsvToFhir(unittest.TestCase):
    """Tests for process_csv_to_fhir function"""

    def setUp(self) -> None:
        GenericSetUp(
            s3_client=s3_client,
            firehose_client=firehose_client,
            dynamodb_client=dynamodb_client,
        )

        redis_getter_patcher = patch("mappings.get_redis_client")
        self.addCleanup(redis_getter_patcher.stop)
        mock_redis = Mock()
        mock_redis_getter = redis_getter_patcher.start()
        mock_redis.hget.return_value = json.dumps(
            [
                {
                    "code": "55735004",
                    "term": "Respiratory syncytial virus infection (disorder)",
                }
            ]
        )
        mock_redis_getter.return_value = mock_redis

    def tearDown(self) -> None:
        GenericTearDown(
            s3_client=s3_client,
            firehose_client=firehose_client,
            dynamodb_client=dynamodb_client,
        )

    @staticmethod
    def upload_source_file(file_key, file_content):
        """
        Uploads a test file with the test_file.file_key (Flu EMIS file) the given file content to the source bucket
        """
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=file_key, Body=file_content)

    def test_process_csv_to_fhir_full_permissions(self):
        """
        Tests that process_csv_to_fhir sends a message to kinesis for each row in the csv when the supplier has full
        permissions
        """
        expected_table_entry = {
            **test_file.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
            "record_count": {"N": "3"},
        }
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_file(
            file_key=test_file.file_key,
            file_content=ValidMockFileContent.with_new_and_update_and_delete,
        )

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_full_permissions_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 3)

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])
        self.assertIn(expected_table_entry, table_items)

    def test_process_csv_to_fhir_partial_permissions(self):
        """
        Tests that process_csv_to_fhir sends a message to kinesis for each row in the csv when the supplier has
        partial permissions
        """
        expected_table_entry = {
            **test_file.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
            "record_count": {"N": "3"},
        }
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_file(
            file_key=test_file.file_key,
            file_content=ValidMockFileContent.with_new_and_update_and_delete,
        )

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_create_permissions_only_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 3)

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])
        self.assertIn(expected_table_entry, table_items)

    def test_process_csv_to_fhir_no_permissions(self):
        """Tests that process_csv_to_fhir does not send fhir_json to kinesis when the supplier has no permissions"""
        expected_table_entry = {
            **test_file.audit_table_entry,
            "status": {"S": FileStatus.PREPROCESSED},
            "record_count": {"N": "2"},
        }
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_file(
            file_key=test_file.file_key,
            file_content=ValidMockFileContent.with_update_and_delete,
        )

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_create_permissions_only_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 2)
        for (
            _supplier,
            message_body,
            _vaccine,
        ), _kwargs in mock_send_to_kinesis.call_args_list:
            self.assertIn("diagnostics", message_body)
            self.assertNotIn("fhir_json", message_body)

        table_items = dynamodb_client.scan(TableName=AUDIT_TABLE_NAME).get("Items", [])
        self.assertIn(expected_table_entry, table_items)

    def test_process_csv_to_fhir_invalid_headers(self):
        """Tests that process_csv_to_fhir does not send a message to kinesis when the csv has invalid headers"""
        self.upload_source_file(
            file_key=test_file.file_key,
            file_content=ValidMockFileContent.with_new_and_update.replace("NHS_NUMBER", "NHS_NUMBERS"),
        )

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_full_permissions_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 0)


if __name__ == "__main__":
    unittest.main()
