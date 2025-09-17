"""Tests for process_csv_to_fhir function"""
import json
import unittest
from unittest.mock import patch
from copy import deepcopy
import boto3
from moto import mock_s3, mock_firehose, mock_dynamodb

from tests.utils_for_recordprocessor_tests.generic_setup_and_teardown import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFileDetails,
    ValidMockFileContent,
    REGION_NAME,
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT, BucketNames

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from batch_processor import process_csv_to_fhir

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
        GenericSetUp(s3_client=s3_client, firehose_client=firehose_client, dynamodb_client=dynamodb_client)

        redis_patcher = patch("mappings.redis_client")
        self.addCleanup(redis_patcher.stop)
        mock_redis_client = redis_patcher.start()
        mock_redis_client.hget.return_value = json.dumps([{
            "code": "55735004",
            "term": "Respiratory syncytial virus infection (disorder)"
        }])

    def tearDown(self) -> None:
        GenericTearDown(s3_client=s3_client, firehose_client=firehose_client, dynamodb_client=dynamodb_client)

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
        self.upload_source_file(
            file_key=test_file.file_key, file_content=ValidMockFileContent.with_new_and_update_and_delete
        )

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_full_permissions_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 3)

    def test_process_csv_to_fhir_partial_permissions(self):
        """
        Tests that process_csv_to_fhir sends a message to kinesis for each row in the csv when the supplier has
        partial permissions
        """
        self.upload_source_file(
            file_key=test_file.file_key, file_content=ValidMockFileContent.with_new_and_update_and_delete
        )

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_create_permissions_only_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 3)

    def test_process_csv_to_fhir_no_permissions(self):
        """Tests that process_csv_to_fhir does not send fhir_json to kinesis when the supplier has no permissions"""
        self.upload_source_file(file_key=test_file.file_key, file_content=ValidMockFileContent.with_update_and_delete)

        with patch("batch_processor.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_create_permissions_only_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 2)
        for (_supplier, message_body, _vaccine), _kwargs in mock_send_to_kinesis.call_args_list:
            self.assertIn("diagnostics", message_body)
            self.assertNotIn("fhir_json", message_body)

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
