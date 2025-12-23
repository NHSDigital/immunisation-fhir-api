import datetime
import json
import unittest
import uuid
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch

import boto3
from moto import mock_aws

from common.data_quality.completeness import MissingFields
from common.data_quality.reporter import DataQualityReport, DataQualityReporter
from test_common.data_quality.sample_values import VALID_BATCH_IMMUNISATION, VALID_FHIR_IMMUNISATION


@mock_aws
class TestDataQualityReporter(unittest.TestCase):
    def setUp(self):
        # Fix date.today() for all validation tests
        date_today_patcher = patch("common.data_quality.models.immunization_batch_row_model.datetime", wraps=datetime)
        self.mock_date_today = date_today_patcher.start()
        self.mock_date_today.date.today.return_value = datetime.date(2024, 5, 20)

        # Fix datetime.now
        self.mock_fixed_datetime = datetime.datetime(2024, 5, 20, 14, 12, 30, 123, tzinfo=datetime.timezone.utc)
        datetime_now_patcher = patch("common.data_quality.checker.datetime", wraps=datetime.datetime)
        self.mock_datetime_now = datetime_now_patcher.start()
        self.mock_datetime_now.now.return_value = self.mock_fixed_datetime

        # Fix generated UUID
        self.example_uuid = uuid.UUID("fa711f35-c08b-48c8-b498-3b151e686ddf")
        uuid_patcher = patch("uuid.uuid4", return_value=self.example_uuid)
        self.mock_uuid = uuid_patcher.start()

        # Set up mock S3 bucket
        self.bucket = "test_bucket"
        self.s3_client = boto3.client("s3")
        self.s3_client.create_bucket(Bucket=self.bucket)

        # Instantiate reporters
        self.batch_dq_reporter = DataQualityReporter(is_batch_csv=True, bucket=self.bucket)
        self.fhir_json_dq_reporter = DataQualityReporter(is_batch_csv=False, bucket=self.bucket)

        # Expected reports
        self.expected_dq_report_no_issues = DataQualityReport(
            data_quality_report_id=str(self.example_uuid),
            validationDate="2024-05-20T14:12:30.000Z",
            completeness=MissingFields(required_fields=[], mandatory_fields=[], optional_fields=[]),
            validity=[],
            timeliness_recorded_days=4,
            timeliness_ingested_seconds=785550,
        )
        self.expected_dq_report_with_issues = DataQualityReport(
            data_quality_report_id=str(self.example_uuid),
            validationDate="2024-05-20T14:12:30.000Z",
            completeness=MissingFields(
                required_fields=["NHS_NUMBER", "INDICATION_CODE"],
                mandatory_fields=["PERSON_FORENAME", "PERSON_SURNAME"],
                optional_fields=["PERFORMING_PROFESSIONAL_FORENAME", "PERFORMING_PROFESSIONAL_SURNAME"],
            ),
            validity=["NHS_NUMBER", "DOSE_AMOUNT", "INDICATION_CODE"],
            timeliness_recorded_days=4,
            timeliness_ingested_seconds=785550,
        )

    def generate_and_send_report_test_logic(
        self, expected_dq_report: DataQualityReport, immunisation: dict, is_batch_csv: bool
    ):
        # run generate report
        if is_batch_csv:
            self.batch_dq_reporter.generate_and_send_report(immunisation)
        else:
            self.fhir_json_dq_reporter.generate_and_send_report(immunisation)

        expected_json = json.dumps(asdict(expected_dq_report))

        actual_json_object = self.s3_client.get_object(Bucket=self.bucket, Key=f"{str(self.example_uuid)}.json")
        actual_json = actual_json_object.get("Body").read().decode("utf-8")

        self.assertEqual(expected_json, actual_json)

    def test_generate_and_send_report_no_issues_batch(self):
        self.generate_and_send_report_test_logic(
            expected_dq_report=self.expected_dq_report_no_issues,
            immunisation=VALID_BATCH_IMMUNISATION,
            is_batch_csv=True,
        )

    def test_generate_and_send_report_no_issues_api(self):
        self.generate_and_send_report_test_logic(
            expected_dq_report=self.expected_dq_report_no_issues,
            immunisation=VALID_FHIR_IMMUNISATION,
            is_batch_csv=False,
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

        self.generate_and_send_report_test_logic(
            expected_dq_report=self.expected_dq_report_with_issues,
            immunisation=batch_immunisation_with_issues,
            is_batch_csv=True,
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

        self.generate_and_send_report_test_logic(
            expected_dq_report=self.expected_dq_report_with_issues,
            immunisation=fhir_immunisation_with_issues,
            is_batch_csv=False,
        )
