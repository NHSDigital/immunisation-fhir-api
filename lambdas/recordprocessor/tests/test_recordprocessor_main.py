"Tests for main function for RecordProcessor"

import json
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from json import JSONDecodeError
from unittest.mock import ANY, Mock, patch

from boto3 import client as boto3_client
from moto import mock_dynamodb, mock_firehose, mock_kinesis, mock_s3

from utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
    Firehose,
    Kinesis,
)
from utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
    add_entry_to_table,
    assert_audit_table_entry,
    create_patch,
)
from utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    REGION_NAME,
    FileDetails,
    InfAckFileRows,
    MockFhirImmsResources,
    MockFieldDictionaries,
    MockFileDetails,
    MockLocalIds,
    ValidMockFileContent,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from batch_processor import main
    from constants import (
        AUDIT_TABLE_NAME,
        AuditTableKeys,
        Diagnostics,
        FileNotProcessedReason,
        FileStatus,
    )

s3_client = boto3_client("s3", region_name=REGION_NAME)
kinesis_client = boto3_client("kinesis", region_name=REGION_NAME)
firehose_client = boto3_client("firehose", region_name=REGION_NAME)
dynamo_db_client = boto3_client("dynamodb", region_name=REGION_NAME)
yesterday = datetime.now(timezone.utc) - timedelta(days=1)
mock_rsv_emis_file = MockFileDetails.rsv_emis


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_dynamodb
@mock_s3
@mock_kinesis
@mock_firehose
class TestRecordProcessor(unittest.TestCase):
    """Tests for main function for RecordProcessor"""

    def setUp(self) -> None:
        GenericSetUp(s3_client, firehose_client, kinesis_client, dynamo_db_client)

        mock_redis = Mock()
        redis_getter_patcher = patch("mappings.get_redis_client")
        batch_processor_logger_patcher = patch("batch_processor.logger")
        self.addCleanup(redis_getter_patcher.stop)
        self.mock_batch_processor_logger = batch_processor_logger_patcher.start()
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
        self.mock_logger_info = create_patch("logging.Logger.info")
        self.mock_set_audit_table_ingestion_start_time = create_patch(
            "file_level_validation.set_audit_table_ingestion_start_time"
        )

    def tearDown(self) -> None:
        patch.stopall()
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

    def make_data_quality_assertions(self, expected_number_of_files: int) -> None:
        """Asserts that the expected data quality reports were submitted"""
        dq_reports = s3_client.list_objects_v2(Bucket=BucketNames.DATA_QUALITY).get("Contents", [])
        self.assertEqual(len(dq_reports), expected_number_of_files)

        for report in dq_reports:
            content = s3_client.get_object(Bucket=BucketNames.DATA_QUALITY, Key=report.get("Key"))
            dq_report_dict = json.loads(content["Body"].read().decode("utf-8"))
            self.maxDiff = None

            self.assertEqual(
                dq_report_dict,
                {
                    "data_quality_report_id": ANY,
                    "validation_date": ANY,
                    "completeness": {"mandatory_fields": [], "optional_fields": [], "required_fields": []},
                    "validity": [],
                    "timeliness_ingested_seconds": ANY,
                    "timeliness_recorded_days": ANY,
                },
            )

    def make_eof_message_assertion(self, file_details: FileDetails, actual_msg: str, total_records: int) -> None:
        self.assertDictEqual(
            {
                "message": "EOF",
                "file_key": file_details.file_key,
                "row_id": f"{file_details.message_id}^{total_records}",
                "supplier": file_details.supplier,
                "vax_type": file_details.vaccine_type,
                "created_at_formatted_string": file_details.created_at_formatted_string,
            },
            json.loads(actual_msg),
        )

    def make_inf_ack_assertions(self, file_details: FileDetails, passed_validation: bool):
        """Asserts that the InfAck file content is as expected"""
        actual_content = self.get_ack_file_content(file_details.inf_ack_file_key)
        actual_rows = actual_content.splitlines()

        expected_row = InfAckFileRows.success_row if passed_validation else InfAckFileRows.failure_row
        expected_row = expected_row.replace("message_id", file_details.message_id).replace(
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

        kinesis_records = kinesis_client.get_records(ShardIterator=self.get_shard_iterator(), Limit=10)["Records"]
        previous_approximate_arrival_time_stamp = yesterday  # Initialise with a time prior to the running of the test

        for test_name, index, expected_kinesis_data, expect_success in test_cases:
            with self.subTest(test_name):
                kinesis_record = kinesis_records[index]
                self.assertEqual(kinesis_record["PartitionKey"], mock_rsv_emis_file.queue_name)
                self.assertEqual(kinesis_record["SequenceNumber"], f"{index + 1}")

                # Ensure that arrival times are sequential
                approximate_arrival_timestamp = kinesis_record["ApproximateArrivalTimestamp"]
                self.assertGreater(
                    approximate_arrival_timestamp,
                    previous_approximate_arrival_time_stamp,
                )
                previous_approximate_arrival_time_stamp = approximate_arrival_timestamp

                kinesis_data = json.loads(kinesis_record["Data"].decode("utf-8"), parse_float=Decimal)
                expected_kinesis_data = {
                    "row_id": f"{mock_rsv_emis_file.message_id}^{index + 1}",
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

        self.make_eof_message_assertion(mock_rsv_emis_file, kinesis_records[-1]["Data"], len(test_cases))

    def assert_object_moved_to_archive(self, file_key: str) -> None:
        """Checks that the S3 object was moved to the archive directory"""
        with self.assertRaises(s3_client.exceptions.NoSuchKey):
            s3_client.get_object(Bucket=BucketNames.SOURCE, Key=f"processing/{file_key}")

        response = s3_client.get_object(Bucket=BucketNames.SOURCE, Key=f"archive/{file_key}")
        self.assertIsNotNone(response)

    def test_e2e_full_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier has
        full permissions.
        """
        test_file = mock_rsv_emis_file
        self.upload_source_files(ValidMockFileContent.with_new_and_update_and_delete)
        add_entry_to_table(test_file, FileStatus.PROCESSING)

        main(test_file.event_full_permissions)

        # Assertion case tuples are structured as
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
                    "local_id": MockLocalIds.COVID_001_RAVS,
                },
                True,
            ),
            (
                "DELETE success",
                2,
                {
                    "operation_requested": "DELETE",
                    "local_id": MockLocalIds.COVID_001_RAVS,
                },
                True,
            ),
        ]
        self.make_inf_ack_assertions(file_details=mock_rsv_emis_file, passed_validation=True)
        self.make_kinesis_assertions(assertion_cases)
        self.make_data_quality_assertions(len(assertion_cases))
        assert_audit_table_entry(test_file, FileStatus.PREPROCESSED, row_count=3)

    def test_e2e_partial_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier only has CREATE
        permissions.
        """
        test_file = mock_rsv_emis_file
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_files(ValidMockFileContent.with_new_and_update_and_delete)

        main(test_file.event_create_permissions_only)

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
                    "local_id": MockLocalIds.COVID_001_RAVS,
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
                    "local_id": MockLocalIds.COVID_001_RAVS,
                },
                False,
            ),
        ]
        self.make_inf_ack_assertions(file_details=mock_rsv_emis_file, passed_validation=True)
        self.make_kinesis_assertions(assertion_cases)
        assert_audit_table_entry(test_file, FileStatus.PREPROCESSED, row_count=3)

    def test_e2e_no_required_permissions(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when the supplier has CREATE permissions
        only.
        """
        test_file = mock_rsv_emis_file
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_files(ValidMockFileContent.with_update_and_delete)

        main(test_file.event_create_permissions_only)

        kinesis_records = kinesis_client.get_records(ShardIterator=self.get_shard_iterator(), Limit=10)["Records"]

        # No. of records = 2 plus EoF message = 3
        self.assertEqual(len(kinesis_records), 3)

        for i in range(len(kinesis_records) - 1):
            data_bytes = kinesis_records[i]["Data"]
            data_dict = json.loads(data_bytes)
            self.assertIn("diagnostics", data_dict)
            self.assertNotIn("fhir_json", data_dict)

        self.make_eof_message_assertion(mock_rsv_emis_file, kinesis_records[-1]["Data"], 2)
        self.make_inf_ack_assertions(file_details=mock_rsv_emis_file, passed_validation=True)
        assert_audit_table_entry(test_file, FileStatus.PREPROCESSED, row_count=2)

    def test_e2e_no_permissions(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when the supplier has no permissions.
        """
        test_file = mock_rsv_emis_file
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_files(ValidMockFileContent.with_update_and_delete)

        main(test_file.event_no_permissions)

        kinesis_records = kinesis_client.get_records(ShardIterator=self.get_shard_iterator(), Limit=10)["Records"]
        table_entry = dynamo_db_client.get_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_file.message_id}},
        ).get("Item")
        self.assertEqual(len(kinesis_records), 0)
        self.make_inf_ack_assertions(file_details=mock_rsv_emis_file, passed_validation=False)
        self.assertDictEqual(
            table_entry,
            {
                **test_file.audit_table_entry,
                "status": {"S": f"{FileStatus.NOT_PROCESSED} - {FileNotProcessedReason.UNAUTHORISED}"},
                "error_details": {"S": "EMIS does not have permissions to perform any of the requested actions."},
            },
        )

    def test_e2e_invalid_action_flags(self):
        """Tests that file is successfully processed when the ACTION_FLAG field is empty or invalid."""
        test_file = mock_rsv_emis_file
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_files(
            ValidMockFileContent.with_update_and_delete.replace("update", "").replace("delete", "INVALID")
        )

        main(test_file.event_full_permissions)

        expected_kinesis_data = {
            "diagnostics": {
                "error_type": "INVALID_ACTION_FLAG",
                "statusCode": 400,
                "error_message": Diagnostics.INVALID_ACTION_FLAG,
            },
            "operation_requested": "TO DEFINE",
            "local_id": MockLocalIds.COVID_001_RAVS,
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
        self.make_inf_ack_assertions(file_details=mock_rsv_emis_file, passed_validation=True)
        self.make_kinesis_assertions(assertion_cases)

    def test_e2e_differing_amounts_of_data(self):
        """Tests that file containing rows with differing amounts of data present is processed as expected"""
        # Create file content with different amounts of data present in each row
        test_file = mock_rsv_emis_file
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        headers = "|".join(MockFieldDictionaries.all_fields.keys())
        all_fields_values = "|".join(f'"{v}"' for v in MockFieldDictionaries.all_fields.values())
        mandatory_fields_only_values = "|".join(f'"{v}"' for v in MockFieldDictionaries.mandatory_fields_only.values())
        critical_fields_only_values = "|".join(f'"{v}"' for v in MockFieldDictionaries.critical_fields_only.values())
        file_content = f"{headers}\n{all_fields_values}\n{mandatory_fields_only_values}\n{critical_fields_only_values}"
        self.upload_source_files(file_content)

        main(test_file.event_full_permissions)

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
        self.make_inf_ack_assertions(file_details=mock_rsv_emis_file, passed_validation=True)
        self.make_kinesis_assertions(test_cases)

    def test_e2e_kinesis_failed(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, when the kinesis send fails, the
        ack file is created and documents an error.
        """
        test_file = mock_rsv_emis_file
        add_entry_to_table(test_file, FileStatus.PROCESSING)
        self.upload_source_files(ValidMockFileContent.with_new_and_update)
        # Delete the kinesis stream, to cause kinesis send to fail
        kinesis_client.delete_stream(StreamName=Kinesis.STREAM_NAME, EnforceConsumerDeletion=True)

        with (  # noqa: E999
            patch("common.log_decorator.send_log_to_firehose") as mock_send_log_to_firehose,  # noqa: E999
            patch("logging_decorator.datetime") as mock_datetime,  # noqa: E999
            patch("logging_decorator.time") as mock_start_time,  # noqa: E999
            patch("common.log_decorator.time") as mock_end_time,  # noqa: E999
        ):  # noqa: E999
            mock_start_time.time.return_value = 1672531200
            mock_end_time.time.return_value = 1672531200.123456
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            main(test_file.event_full_permissions)

        # Since the failure occurred at row level, not file level, the ack file should still be created
        # and firehose logs should indicate a successful file level validation
        table_entry = dynamo_db_client.get_item(
            TableName=AUDIT_TABLE_NAME,
            Key={AuditTableKeys.MESSAGE_ID: {"S": test_file.message_id}},
        ).get("Item")
        self.make_inf_ack_assertions(file_details=test_file, passed_validation=True)
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
        mock_send_log_to_firehose.assert_called_with(Firehose.STREAM_NAME, expected_log_data)
        self.assertDictEqual(
            table_entry,
            {
                **test_file.audit_table_entry,
                "status": {"S": FileStatus.FAILED},
                "error_details": {
                    "S": "An error occurred (ResourceNotFoundException) when calling the PutRecord operation"
                    ": Stream imms-batch-internal-dev-processingdata-stream under account 123456789012"
                    " not found."
                },
            },
        )

    def test_e2e_empty_file_is_flagged_and_processed_correctly(self):
        """
        Tests files that contain only the headers and no records are marked as empty and moved to archive.
        """
        test_cases = [
            ("File containing only headers", ValidMockFileContent.headers),
            (
                "File containing headers and new line",
                ValidMockFileContent.headers + "\n",
            ),
            (
                "File containing headers and multiple new lines",
                ValidMockFileContent.empty_file_with_multiple_new_lines,
            ),
        ]
        for description, file_content in test_cases:
            with self.subTest(description=description):
                self.mock_batch_processor_logger.reset_mock()
                test_file = mock_rsv_emis_file
                self.upload_source_files(file_content)
                add_entry_to_table(test_file, FileStatus.PROCESSING)

                main(test_file.event_full_permissions)

                kinesis_records = kinesis_client.get_records(ShardIterator=self.get_shard_iterator(), Limit=10)[
                    "Records"
                ]

                self.mock_batch_processor_logger.warning.assert_called_once_with(
                    "File was empty: %s. Moving file to archive directory.",
                    "RSV_Vaccinations_v5_8HK48_20210730T12000000.csv",
                )
                self.assertListEqual(kinesis_records, [])
                assert_audit_table_entry(test_file, "Not processed - Empty file", row_count=0)
                self.assert_object_moved_to_archive(test_file.file_key)

    def test_e2e_error_is_logged_if_invalid_json_provided(self):
        """This scenario should not happen. If it does, it means our batch processing system config is broken and we
        have received malformed content from SQS -> EventBridge. In this case we log the error so we will be alerted.
        However, we cannot do anything with the AuditDB record as we cannot retrieve information from the event
        """
        malformed_event = '{"test": {}'
        main(malformed_event)

        logged_message = self.mock_batch_processor_logger.error.call_args[0][0]
        exception = self.mock_batch_processor_logger.error.call_args[0][1]
        self.assertEqual(logged_message, "Error decoding incoming message: %s")
        self.assertIsInstance(exception, JSONDecodeError)


if __name__ == "__main__":
    unittest.main()
