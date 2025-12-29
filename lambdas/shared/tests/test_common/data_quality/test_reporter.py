import datetime
import json
import unittest
import uuid
from copy import deepcopy
from unittest.mock import patch

import boto3
from moto import mock_aws

from common.data_quality.reporter import DataQualityReporter
from test_common.data_quality.sample_values import VALID_BATCH_IMMUNISATION, VALID_FHIR_IMMUNISATION


@mock_aws
class TestDataQualityReporter(unittest.TestCase):
    def setUp(self):
        # Fix date.today() in validator model
        date_today_patcher = patch("common.data_quality.models.immunization_batch_row_model.datetime", wraps=datetime)
        mock_date_today = date_today_patcher.start()
        mock_date_today.date.today.return_value = datetime.date(2024, 5, 20)

        # Fix datetime.now() in dq checker to fix the report datetime
        datetime_now_patcher = patch("common.data_quality.checker.datetime", wraps=datetime.datetime)
        mock_datetime_now = datetime_now_patcher.start()
        mock_datetime_now.now.return_value = datetime.datetime(
            2024, 5, 20, 14, 12, 30, 123, tzinfo=datetime.timezone.utc
        )

        # Fix generated UUID
        self.example_uuid = uuid.UUID("fa711f35-c08b-48c8-b498-3b151e686ddf")
        uuid_patcher = patch("uuid.uuid4", return_value=self.example_uuid)
        uuid_patcher.start()

        # Mock logger
        logger_patcher = patch("common.data_quality.reporter.logger")
        self.mock_logger = logger_patcher.start()

        # Set up mock S3 bucket
        self.bucket = "test_bucket"
        self.s3_client = boto3.client("s3")
        self.s3_client.create_bucket(Bucket=self.bucket)

        # Instantiate reporters
        self.batch_dq_reporter = DataQualityReporter(is_batch_csv=True, bucket=self.bucket)
        self.fhir_json_dq_reporter = DataQualityReporter(is_batch_csv=False, bucket=self.bucket)

        # Expected reports
        self.expected_dq_report_no_issues = json.dumps(
            {
                "data_quality_report_id": str(self.example_uuid),
                "validation_date": "2024-05-20T14:12:30.000Z",
                "completeness": {"required_fields": [], "mandatory_fields": [], "optional_fields": []},
                "validity": [],
                "timeliness_recorded_days": 4,
                "timeliness_ingested_seconds": 785550,
            }
        )
        self.expected_dq_report_with_issues = json.dumps(
            {
                "data_quality_report_id": str(self.example_uuid),
                "validation_date": "2024-05-20T14:12:30.000Z",
                "completeness": {
                    "required_fields": ["NHS_NUMBER", "INDICATION_CODE"],
                    "mandatory_fields": ["PERSON_FORENAME", "PERSON_SURNAME"],
                    "optional_fields": ["PERFORMING_PROFESSIONAL_FORENAME", "PERFORMING_PROFESSIONAL_SURNAME"],
                },
                "validity": ["NHS_NUMBER", "DOSE_AMOUNT", "INDICATION_CODE"],
                "timeliness_recorded_days": 4,
                "timeliness_ingested_seconds": 785550,
            }
        )

    def tearDown(self):
        patch.stopall()

    def get_report_from_test_bucket(self) -> str:
        expected_object = self.s3_client.get_object(Bucket=self.bucket, Key=f"{str(self.example_uuid)}.json")
        return expected_object.get("Body").read().decode("utf-8")

    def test_generate_and_send_report_no_issues_batch(self):
        self.batch_dq_reporter.generate_and_send_report(VALID_BATCH_IMMUNISATION)

        submitted_report = self.get_report_from_test_bucket()

        self.assertEqual(submitted_report, self.expected_dq_report_no_issues)
        self.mock_logger.info.assert_called_once_with(
            "Data quality report sent successfully with ID: %s", str(self.example_uuid)
        )

    def test_generate_and_send_report_no_issues_api(self):
        self.fhir_json_dq_reporter.generate_and_send_report(VALID_FHIR_IMMUNISATION)

        submitted_report = self.get_report_from_test_bucket()

        self.assertEqual(submitted_report, self.expected_dq_report_no_issues)
        self.mock_logger.info.assert_called_once_with(
            "Data quality report sent successfully with ID: %s", str(self.example_uuid)
        )

    def test_generate_and_send_report_with_issues_batch(self):
        batch_immunisation_with_issues = deepcopy(VALID_BATCH_IMMUNISATION)

        # Missing fields
        batch_immunisation_with_issues.pop("NHS_NUMBER")  # required
        batch_immunisation_with_issues.pop("INDICATION_CODE")  # required
        batch_immunisation_with_issues.pop("PERSON_FORENAME")  # mandatory
        batch_immunisation_with_issues.pop("PERSON_SURNAME")  # mandatory
        batch_immunisation_with_issues.pop("PERFORMING_PROFESSIONAL_FORENAME")  # optional
        batch_immunisation_with_issues.pop("PERFORMING_PROFESSIONAL_SURNAME")  # optional

        # Invalid fields
        batch_immunisation_with_issues["DOSE_AMOUNT"] = "6.789"

        self.batch_dq_reporter.generate_and_send_report(batch_immunisation_with_issues)

        submitted_report = self.get_report_from_test_bucket()

        self.assertEqual(submitted_report, self.expected_dq_report_with_issues)
        self.mock_logger.info.assert_called_once_with(
            "Data quality report sent successfully with ID: %s", str(self.example_uuid)
        )

    def test_generate_and_send_report_with_issues_api(self):
        fhir_immunisation_with_issues = deepcopy(VALID_FHIR_IMMUNISATION)

        # Missing fields
        fhir_immunisation_with_issues["contained"][1]["identifier"][0]["value"] = ""  # required
        fhir_immunisation_with_issues["reasonCode"][0]["coding"][0]["code"] = ""  # required
        fhir_immunisation_with_issues["contained"][1]["name"][0]["given"][0] = ""  # mandatory
        fhir_immunisation_with_issues["contained"][1]["name"][0]["family"] = ""  # mandatory
        fhir_immunisation_with_issues["contained"][0]["name"][0]["given"][0] = ""  # optional
        fhir_immunisation_with_issues["contained"][0]["name"][0]["family"] = ""  # optional

        # Invalid fields
        fhir_immunisation_with_issues["doseQuantity"]["value"] = "6.789"

        self.fhir_json_dq_reporter.generate_and_send_report(fhir_immunisation_with_issues)

        submitted_report = self.get_report_from_test_bucket()

        self.assertEqual(submitted_report, self.expected_dq_report_with_issues)
        self.mock_logger.info.assert_called_once_with(
            "Data quality report sent successfully with ID: %s", str(self.example_uuid)
        )

    def test_generate_and_send_report_logs_boto_error_when_s3_fails(self):
        """Simulates an error scenario where infrastructure configuration is incorrect."""
        dq_reporter_invalid_bucket = DataQualityReporter(is_batch_csv=True, bucket="invalid-bucket-name")
        dq_reporter_invalid_bucket.generate_and_send_report(VALID_BATCH_IMMUNISATION)

        self.mock_logger.info.assert_not_called()
        self.mock_logger.error.assert_called_once_with(
            "Error sending data quality report with ID: %s. Error: %s",
            str(self.example_uuid),
            "An error occurred (NoSuchBucket) when calling the PutObject operation: The specified bucket does not exist",
        )
