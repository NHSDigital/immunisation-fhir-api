"E2e tests for recordprocessor"

import unittest
import json
from decimal import Decimal
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from moto import mock_s3, mock_kinesis
from boto3 import client as boto3_client
from batch_processing import main
from constants import Diagnostics
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    Kinesis,
    MOCK_ENVIRONMENT_DICT,
    MockFileDetails,
    ValidMockFileContent,
    BucketNames,
    MockFhirImmsResources,
    MockFieldDictionaries,
    MockLocalIds,
    REGION_NAME,
)

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client("kinesis", region_name=REGION_NAME)
yesterday = datetime.now(timezone.utc) - timedelta(days=1)
mock_rsv_emis_file = MockFileDetails.rsv_emis


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_kinesis
class TestRecordProcessor(unittest.TestCase):
    """E2e tests for RecordProcessor"""

    def setUp(self) -> None:
        for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME})

        kinesis_client.create_stream(StreamName=Kinesis.STREAM_NAME, ShardCount=1)

    def tearDown(self) -> None:
        # Delete all of the buckets (the contents of each bucket must be deleted first)
        for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

        # Delete the kinesis stream
        try:
            kinesis_client.delete_stream(StreamName=Kinesis.STREAM_NAME, EnforceConsumerDeletion=True)
        except kinesis_client.exceptions.ResourceNotFoundException:
            pass

    @staticmethod
    def upload_files(source_file_content):  # pylint: disable=dangerous-default-value
        """Uploads a test file with the TEST_FILE_KEY (RSV EMIS file) the given file content to the source bucket"""
        s3_client.put_object(Bucket=BucketNames.SOURCE, Key=mock_rsv_emis_file.file_key, Body=source_file_content)

    @staticmethod
    def get_shard_iterator():
        """Obtains and returns a shard iterator"""
        # Obtain the first shard
        stream_name = Kinesis.STREAM_NAME
        response = kinesis_client.describe_stream(StreamName=Kinesis.STREAM_NAME)
        shards = response["StreamDescription"]["Shards"]
        shard_id = shards[0]["ShardId"]

        # Get a shard iterator (using iterator type "TRIM_HORIZON" to read from the beginning)
        return kinesis_client.get_shard_iterator(
            StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]

    @staticmethod
    def get_ack_file_content():
        """Downloads the ack file, decodes its content and returns the decoded content"""
        response = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=mock_rsv_emis_file.ack_file_key)
        return response["Body"].read().decode("utf-8")

    def make_assertions(self, test_cases):
        """
        The input is a list of test_case tuples where each tuple is structured as
        (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success).
        The standard key-value pairs
        {row_id: {TEST_FILE_ID}^{index+1}, file_key: TEST_FILE_KEY, supplier: TEST_SUPPLIER} are added to the
        expected_kinesis_data dictionary before assertions are made.
        For each index, assertions will be made on the record found at the given index in the kinesis response.
        Assertions made:
        * Kinesis PartitionKey is TEST_SUPPLIER
        * Kinesis SequenceNumber is index + 1
        * Kinesis ApproximateArrivalTimestamp is later than the timestamp for the preceeding data row
        * Where expected_success is True:
            - "fhir_json" key is found in the Kinesis data
            - Kinesis Data is equal to the expected_kinesis_data when ignoring the "fhir_json"
        * Where expected_success is False:
            - Kinesis Data is equal to the expected_kinesis_data
        """

        kinesis_records = kinesis_client.get_records(ShardIterator=self.get_shard_iterator(), Limit=10)["Records"]
        previous_approximate_arrival_time_stamp = yesterday  # Initialise with a time prior to the running of the test

        for test_name, index, expected_kinesis_data, expect_success in test_cases:
            with self.subTest(test_name):

                kinesis_record = kinesis_records[index]
                self.assertEqual(kinesis_record["PartitionKey"], mock_rsv_emis_file.supplier)
                self.assertEqual(kinesis_record["SequenceNumber"], f"{index+1}")

                # Ensure that arrival times are sequential
                approximate_arrival_timestamp = kinesis_record["ApproximateArrivalTimestamp"]
                self.assertGreater(approximate_arrival_timestamp, previous_approximate_arrival_time_stamp)
                previous_approximate_arrival_time_stamp = approximate_arrival_timestamp

                kinesis_data = json.loads(kinesis_record["Data"].decode("utf-8"), parse_float=Decimal)
                expected_kinesis_data = {
                    "row_id": f"{mock_rsv_emis_file.message_id}^{index+1}",
                    "file_key": mock_rsv_emis_file.file_key,
                    "supplier": mock_rsv_emis_file.supplier,
                    "vax_type": mock_rsv_emis_file.vaccine_type,
                    "created_at_formatted_string": mock_rsv_emis_file.created_at_formatted_string,
                    **expected_kinesis_data,
                }
                if expect_success and "fhir_json" not in expected_kinesis_data:
                    # Some tests ignore the fhir_json value, so we only need to check that the key is present.
                    key_to_ignore = "fhir_json"
                    self.assertIn(key_to_ignore, kinesis_data)
                    kinesis_data.pop(key_to_ignore)
                self.assertEqual(kinesis_data, expected_kinesis_data)

    def test_e2e_full_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier has
        full permissions.
        """
        self.upload_files(ValidMockFileContent.with_new_and_update_and_delete)

        main(mock_rsv_emis_file.event_full_permissions)

        # Assertion case tuples are stuctured as
        # (test_name, index, expected_kinesis_data_ignoring_fhir_json,expect_success)
        assertion_cases = [
            (
                "CREATE success",
                0,
                {"operation_requested": "CREATE", "local_id": MockLocalIds.RSV_001_RAVS},
                True,
            ),
            (
                "UPDATE success",
                1,
                {"operation_requested": "UPDATE", "local_id": MockLocalIds.COVID19_001_RAVS},
                True,
            ),
            (
                "DELETE success",
                2,
                {"operation_requested": "DELETE", "local_id": MockLocalIds.COVID19_001_RAVS},
                True,
            ),
        ]
        self.make_assertions(assertion_cases)

    def test_e2e_partial_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier only has CREATE
        permissions.
        """
        self.upload_files(ValidMockFileContent.with_new_and_update_and_delete)

        main(mock_rsv_emis_file.event_create_permissions_only)

        # Assertion case tuples are stuctured as
        # (test_name, index, expected_kinesis_data_ignoring_fhir_json,expect_success)
        assertion_cases = [
            (
                "CREATE success",
                0,
                {"operation_requested": "CREATE", "local_id": MockLocalIds.RSV_001_RAVS},
                True,
            ),
            (
                "UPDATE no permissions",
                1,
                {
                    "diagnostics": Diagnostics.NO_PERMISSIONS,
                    "operation_requested": "UPDATE",
                    "local_id": MockLocalIds.COVID19_001_RAVS,
                },
                False,
            ),
            (
                "DELETE no permissions",
                2,
                {
                    "diagnostics": Diagnostics.NO_PERMISSIONS,
                    "operation_requested": "DELETE",
                    "local_id": MockLocalIds.COVID19_001_RAVS,
                },
                False,
            ),
        ]

        self.make_assertions(assertion_cases)

    def test_e2e_no_permissions(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when the supplier has CREATE permissions
        only.
        """
        self.upload_files(ValidMockFileContent.with_update_and_delete)

        main(mock_rsv_emis_file.event_create_permissions_only)

        # TODO: add assertions

    def test_e2e_invalid_action_flags(self):
        """Tests that file is successfully processed when the ACTION_FLAG field is empty or invalid."""

        self.upload_files(
            ValidMockFileContent.with_update_and_delete.replace("update", "").replace("delete", "INVALID")
        )

        main(mock_rsv_emis_file.event_full_permissions)

        expected_kinesis_data = {
            "diagnostics": Diagnostics.INVALID_ACTION_FLAG,
            "operation_requested": "TO DEFINE",
            "local_id": MockLocalIds.COVID19_001_RAVS,
        }

        # Assertion case tuples are stuctured as
        # (test_name, index, expected_kinesis_data_ignoring_fhir_json,expect_success)
        assertion_cases = [
            ("Missing ACTION_FLAG", 0, {**expected_kinesis_data, "operation_requested": ""}, False),
            ("Invalid ACTION_FLAG", 1, {**expected_kinesis_data, "operation_requested": "INVALID"}, False),
        ]

        self.make_assertions(assertion_cases)

    def test_e2e_differing_amounts_of_data(self):
        """Tests that file containing rows with differing amounts of data present is processed as expected"""
        # Create file content with different amounts of data present in each row
        headers = "|".join(MockFieldDictionaries.all_fields.keys())
        all_fields_values = "|".join(f'"{v}"' for v in MockFieldDictionaries.all_fields.values())
        mandatory_fields_only_values = "|".join(f'"{v}"' for v in MockFieldDictionaries.mandatory_fields_only.values())
        critical_fields_only_values = "|".join(f'"{v}"' for v in MockFieldDictionaries.critical_fields_only.values())
        file_content = f"{headers}\n{all_fields_values}\n{mandatory_fields_only_values}\n{critical_fields_only_values}"
        self.upload_files(file_content)

        main(mock_rsv_emis_file.event_full_permissions)

        all_fields_row_expected_kinesis_data = {
            "operation_requested": "UPDATE",
            "fhir_json": MockFhirImmsResources.all_fields,
            "local_id": MockLocalIds.RSV_002_RAVS,
        }

        mandatory_fields_only_row_expected_kinesis_data = {
            "operation_requested": "UPDATE",
            "fhir_json": MockFhirImmsResources.mandatory_fields_only,
            "local_id": MockLocalIds.RSV_002_RAVS,
        }

        critical_fields_only_row_expected_kinesis_data = {
            "operation_requested": "CREATE",
            "fhir_json": MockFhirImmsResources.critical_fields,
            "local_id": "a_unique_id^a_unique_id_uri",
        }

        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data, expect_success)
        test_cases = [
            ("All fields", 0, all_fields_row_expected_kinesis_data, True),
            ("Mandatory fields only", 1, mandatory_fields_only_row_expected_kinesis_data, True),
            ("Critical fields only", 2, critical_fields_only_row_expected_kinesis_data, True),
        ]
        self.make_assertions(test_cases)

    def test_e2e_kinesis_failed(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, when the kinesis send fails, the
        ack file is created and documents an error.
        """
        self.upload_files(ValidMockFileContent.with_new_and_update)
        # Delete the kinesis stream, to cause kinesis send to fail
        kinesis_client.delete_stream(StreamName=Kinesis.STREAM_NAME, EnforceConsumerDeletion=True)

        main(mock_rsv_emis_file.event_full_permissions)

        # TODO: Add assertions


if __name__ == "__main__":
    unittest.main()
