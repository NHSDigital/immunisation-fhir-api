"""Tests for process_csv_to_fhir function"""

import unittest
from unittest.mock import patch
import boto3
from copy import deepcopy
from moto import mock_s3
from batch_processing import process_csv_to_fhir
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MOCK_ENVIRONMENT_DICT,
    MockFileDetails,
    ValidMockFileContent,
    BucketNames,
    REGION_NAME,
)

s3_client = boto3.client("s3", region_name=REGION_NAME)
test_file = MockFileDetails.rsv_emis


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
class TestProcessLambdaFunction(unittest.TestCase):
    """Tests for process_csv_to_fhir function"""

    def setUp(self) -> None:
        for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME})

    def tearDown(self) -> None:
        for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

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

        with patch("batch_processing.send_to_kinesis") as mock_send_to_kinesis:
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

        with patch("batch_processing.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_create_permissions_only_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 3)

    def test_process_csv_to_fhir_no_permissions(self):
        """Tests that process_csv_to_fhir does not send a message to kinesis when the supplier has no permissions"""
        self.upload_source_file(file_key=test_file.file_key, file_content=ValidMockFileContent.with_update_and_delete)

        with patch("batch_processing.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_create_permissions_only_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 0)

    def test_process_csv_to_fhir_invalid_headers(self):
        """Tests that process_csv_to_fhir does not send a message to kinesis when the csv has invalid headers"""
        self.upload_source_file(
            file_key=test_file.file_key,
            file_content=ValidMockFileContent.with_new_and_update.replace("NHS_NUMBER", "NHS_NUMBERS"),
        )

        with patch("batch_processing.send_to_kinesis") as mock_send_to_kinesis:
            process_csv_to_fhir(deepcopy(test_file.event_full_permissions_dict))

        self.assertEqual(mock_send_to_kinesis.call_count, 0)


if __name__ == "__main__":
    unittest.main()
