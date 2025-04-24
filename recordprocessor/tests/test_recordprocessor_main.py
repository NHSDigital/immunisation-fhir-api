"Tests for main function for RecordProcessor"

import unittest
import json
from decimal import Decimal
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from moto import mock_s3, mock_kinesis, mock_firehose
from boto3 import client as boto3_client

from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFileDetails,
    FileDetails,
    ValidMockFileContent,
    MockFhirImmsResources,
    MockFieldDictionaries,
    MockLocalIds,
    InfAckFileRows,
    REGION_NAME,
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
    Kinesis,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import Diagnostics
    from batch_processing import main

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client("kinesis", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
yesterday = datetime.now(timezone.utc) - timedelta(days=1)
mock_rsv_emis_file = MockFileDetails.rsv_emis


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_kinesis
@mock_firehose
class TestRecordProcessor(unittest.TestCase):
    """Tests for main function for RecordProcessor"""

    def setUp(self) -> None:
        GenericSetUp(s3_client, firehose_client, kinesis_client)

    def tearDown(self) -> None:
        GenericTearDown(s3_client, firehose_client, kinesis_client)

    @staticmethod
    def upload_source_files(
        source_file_content,
    ):  # pylint: disable=dangerous-default-value
        """Uploads a test file with the TEST_FILE_KEY (RSV EMIS file) the given file content to the source bucket"""
        s3_client.put_object(
            Bucket=BucketNames.SOURCE,
            Key=mock_rsv_emis_file.file_key,
            Body=source_file_content,
        )

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
    def get_ack_file_content(file_key: str) -> str:
        """Downloads the ack file, decodes its content and returns the decoded content"""
        response = s3_client.get_object(Bucket=BucketNames.DESTINATION, Key=file_key)
        return response["Body"].read().decode("utf-8")

    def make_inf_ack_assertions(
        self, file_details: FileDetails, passed_validation: bool
    ):
        """Asserts that the InfAck file content is as expected"""
        actual_content = self.get_ack_file_content(file_details.inf_ack_file_key)
        actual_rows = actual_content.splitlines()

        expected_row = (
            InfAckFileRows.success_row
            if passed_validation
            else InfAckFileRows.failure_row
        )
        expected_row = expected_row.replace(
            "message_id", file_details.message_id
        ).replace(
            "created_at_formatted_string", file_details.created_at_formatted_string
        )

        self.assertEqual(actual_rows, [InfAckFileRows.HEADERS, expected_row])

    def make_kinesis_assertions(self, test_cases):
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

        kinesis_records = kinesis_client.get_records(
            ShardIterator=self.get_shard_iterator(), Limit=10
        )["Records"]
        previous_approximate_arrival_time_stamp = (
            yesterday  # Initialise with a time prior to the running of the test
        )

        for test_name, index, expected_kinesis_data, expect_success in test_cases:
            with self.subTest(test_name):

                kinesis_record = kinesis_records[index]
                self.assertEqual(
                    kinesis_record["PartitionKey"], mock_rsv_emis_file.queue_name
                )
                self.assertEqual(kinesis_record["SequenceNumber"], f"{index+1}")

                # Ensure that arrival times are sequential
                approximate_arrival_timestamp = kinesis_record[
                    "ApproximateArrivalTimestamp"
                ]
                self.assertGreater(
                    approximate_arrival_timestamp,
                    previous_approximate_arrival_time_stamp,
                )
                previous_approximate_arrival_time_stamp = approximate_arrival_timestamp

                kinesis_data = json.loads(
                    kinesis_record["Data"].decode("utf-8"), parse_float=Decimal
                )
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
        self.upload_source_files(ValidMockFileContent.with_new_and_update_and_delete)

        main(mock_rsv_emis_file.event_full_permissions)

        # Assertion case tuples are stuctured as
        # (test_name, index, expected_kinesis_data_ignoring_fhir_json,expect_success)
        assertion_cases = [
            (
                "CREATE success",
                0,
                {
                    "operation_requested": "CREATE",
                    "local_id": MockLocalIds.RSV_001_RAVS,
                },
                True,
            ),
            (
                "UPDATE success",
                1,
                {
                    "operation_requested": "UPDATE",
                    "local_id": MockLocalIds.COVID19_001_RAVS,
                },
                True,
            ),
            (
                "DELETE success",
                2,
                {
                    "operation_requested": "DELETE",
                    "local_id": MockLocalIds.COVID19_001_RAVS,
                },
                True,
            ),
        ]
        self.make_inf_ack_assertions(
            file_details=mock_rsv_emis_file, passed_validation=True
        )
        self.make_kinesis_assertions(assertion_cases)

    def test_e2e_partial_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier only has CREATE
        permissions.
        """
        self.upload_source_files(ValidMockFileContent.with_new_and_update_and_delete)

        main(mock_rsv_emis_file.event_create_permissions_only)

        # Assertion case tuples are stuctured as
        # (test_name, index, expected_kinesis_data_ignoring_fhir_json,expect_success)
        assertion_cases = [
            (
                "CREATE success",
                0,
                {
                    "operation_requested": "CREATE",
                    "local_id": MockLocalIds.RSV_001_RAVS,
                },
                True,
            ),
            (
                "UPDATE no permissions",
                1,
                {
                    "diagnostics": {
                        "error_type": "NO_PERMISSIONS",
                        "statusCode": 403,
                        "error_message": Diagnostics.NO_PERMISSIONS,
                    },
                    "operation_requested": "UPDATE",
                    "local_id": MockLocalIds.COVID19_001_RAVS,
                },
                False,
            ),
            (
                "DELETE no permissions",
                2,
                {
                    "diagnostics": {
                        "error_type": "NO_PERMISSIONS",
                        "statusCode": 403,
                        "error_message": Diagnostics.NO_PERMISSIONS,
                    },
                    "operation_requested": "DELETE",
                    "local_id": MockLocalIds.COVID19_001_RAVS,
                },
                False,
            ),
        ]
        self.make_inf_ack_assertions(
            file_details=mock_rsv_emis_file, passed_validation=True
        )
        self.make_kinesis_assertions(assertion_cases)

    def test_e2e_no_permissions(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when the supplier has CREATE permissions
        only.
        """
        self.upload_source_files(ValidMockFileContent.with_update_and_delete)

        main(mock_rsv_emis_file.event_create_permissions_only)

        kinesis_records = kinesis_client.get_records(
            ShardIterator=self.get_shard_iterator(), Limit=10
        )["Records"]
        self.assertEqual(len(kinesis_records), 0)
        self.make_inf_ack_assertions(
            file_details=mock_rsv_emis_file, passed_validation=False
        )

    def test_e2e_invalid_action_flags(self):
        """Tests that file is successfully processed when the ACTION_FLAG field is empty or invalid."""

        self.upload_source_files(
            ValidMockFileContent.with_update_and_delete.replace("update", "").replace(
                "delete", "INVALID"
            )
        )

        main(mock_rsv_emis_file.event_full_permissions)

        expected_kinesis_data = {
            "diagnostics": {
                "error_type": "INVALID_ACTION_FLAG",
                "statusCode": 400,
                "error_message": Diagnostics.INVALID_ACTION_FLAG,
            },
            "operation_requested": "TO DEFINE",
            "local_id": MockLocalIds.COVID19_001_RAVS,
        }

        # Assertion case tuples are stuctured as
        # (test_name, index, expected_kinesis_data_ignoring_fhir_json,expect_success)
        assertion_cases = [
            (
                "Missing ACTION_FLAG",
                0,
                {**expected_kinesis_data, "operation_requested": ""},
                False,
            ),
            (
                "Invalid ACTION_FLAG",
                1,
                {**expected_kinesis_data, "operation_requested": "INVALID"},
                False,
            ),
        ]
        self.make_inf_ack_assertions(
            file_details=mock_rsv_emis_file, passed_validation=True
        )
        self.make_kinesis_assertions(assertion_cases)

    def test_e2e_differing_amounts_of_data(self):
        """Tests that file containing rows with differing amounts of data present is processed as expected"""
        # Create file content with different amounts of data present in each row
        headers = "|".join(MockFieldDictionaries.all_fields.keys())
        all_fields_values = "|".join(
            f'"{v}"' for v in MockFieldDictionaries.all_fields.values()
        )
        mandatory_fields_only_values = "|".join(
            f'"{v}"' for v in MockFieldDictionaries.mandatory_fields_only.values()
        )
        critical_fields_only_values = "|".join(
            f'"{v}"' for v in MockFieldDictionaries.critical_fields_only.values()
        )
        file_content = f"{headers}\n{all_fields_values}\n{mandatory_fields_only_values}\n{critical_fields_only_values}"
        self.upload_source_files(file_content)

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
            (
                "Mandatory fields only",
                1,
                mandatory_fields_only_row_expected_kinesis_data,
                True,
            ),
            (
                "Critical fields only",
                2,
                critical_fields_only_row_expected_kinesis_data,
                True,
            ),
        ]
        self.make_inf_ack_assertions(
            file_details=mock_rsv_emis_file, passed_validation=True
        )
        self.make_kinesis_assertions(test_cases)

    def test_e2e_kinesis_failed(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, when the kinesis send fails, the
        ack file is created and documents an error.
        """
        self.upload_source_files(ValidMockFileContent.with_new_and_update)
        # Delete the kinesis stream, to cause kinesis send to fail
        kinesis_client.delete_stream(
            StreamName=Kinesis.STREAM_NAME, EnforceConsumerDeletion=True
        )

        with (  # noqa: E999
            patch(
                "logging_decorator.send_log_to_firehose"
            ) as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.datetime") as mock_datetime,  # noqa: E999
            patch("logging_decorator.time") as mock_time,  # noqa: E999
        ):  # noqa: E999
            mock_time.time.side_effect = [1672531200, 1672531200.123456]
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            main(mock_rsv_emis_file.event_full_permissions)

        # Since the failure occured at row level, not file level, the ack file should still be created
        # and firehose logs should indicate a successful file level validation
        self.make_inf_ack_assertions(
            file_details=mock_rsv_emis_file, passed_validation=True
        )
        expected_log_data = {
            "function_name": "record_processor_file_level_validation",
            "date_time": "2024-01-01 12:00:00",
            "file_key": "RSV_Vaccinations_v5_8HK48_20210730T12000000.csv",
            "message_id": "rsv_emis_test_id",
            "vaccine_type": "RSV",
            "supplier": "EMIS",
            "time_taken": "0.12346s",
            "statusCode": 200,
            "message": "Successfully sent for record processing",
        }
        mock_send_log_to_firehose.assert_called_with(expected_log_data)


if __name__ == "__main__":
    unittest.main()
