import copy
import datetime
import unittest
from unittest.mock import patch

from common.data_quality.checker import DataQualityChecker, DataQualityOutput
from test_common.data_quality.sample_values import VALID_BATCH_IMMUNISATION, VALID_FHIR_IMMUNISATION


class TestDataQualityChecker(unittest.TestCase):
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

        self.batch_dq_checker = DataQualityChecker(is_batch_csv=True)
        self.fhir_json_dq_checker = DataQualityChecker(is_batch_csv=False)

    def assert_successful_result(self, result: DataQualityOutput) -> None:
        self.assertEqual([], result.missing_fields.optional_fields)
        self.assertEqual([], result.missing_fields.mandatory_fields)
        self.assertEqual([], result.missing_fields.required_fields)
        self.assertEqual([], result.invalid_fields)
        self.assertEqual(4, result.timeliness.recorded_timeliness_days)
        self.assertEqual(785550, result.timeliness.ingested_timeliness_seconds)

    def test_check_validity_returns_empty_list_when_data_is_valid(self):
        validation_result = self.batch_dq_checker._check_validity(VALID_BATCH_IMMUNISATION)

        self.assertEqual([], validation_result)

    def test_check_validity_returns_list_of_invalid_fields_when_invalid_data_provided(self):
        test_cases = [
            ("NHS_NUMBER", "1234"),  # Failing min length
            ("NHS_NUMBER", "1234543543543543534"),  # Failing max length
            ("NHS_NUMBER", "900000AB09"),  # Failing digit only check
            ("PERSON_DOB", "18990101"),  # Prior to min accepted past date
            ("PERSON_DOB", "20240137"),  # Invalid date
            ("PERSON_DOB", "20240624"),  # Past dates only
            ("DATE_AND_TIME", "17000511T120000"),  # Prior to min accepted past date
            ("DATE_AND_TIME", "20241511T120000"),  # Invalid datetime
            ("DATE_AND_TIME", "20241511T120"),  # Invalid datetime
            ("DATE_AND_TIME", "20240520T120001"),  # Past dates only
            ("PERSON_POSTCODE", "AAA12 3B"),
            ("EXPIRY_DATE", "18990101"),  # Prior to min accepted past date
            ("EXPIRY_DATE", "20240137"),  # Invalid date
            ("EXPIRY_DATE", "20250521"),  # Expiry greater than a year away
            ("DOSE_AMOUNT", "abd"),  # Not a decimal value
            ("DOSE_AMOUNT", "5.67"),  # Decimal value but not in the permitted list of values
            ("SITE_OF_VACCINATION_CODE", "1254"),  # Fails snomed code min length
            ("SITE_OF_VACCINATION_CODE", "12321432543543543534"),  # Fails snomed code max length
            ("SITE_OF_VACCINATION_CODE", "18756hg098"),  # Fails regex
            ("ROUTE_OF_VACCINATION_CODE", "1254"),  # Fails snomed code min length
            ("ROUTE_OF_VACCINATION_CODE", "12321432543543543534"),  # Fails snomed code max length
            ("ROUTE_OF_VACCINATION_CODE", "18756hg098"),  # Fails regex
            ("DOSE_UNIT_CODE", "415818088"),  # Dose unit code not in the enums
            ("INDICATION_CODE", "1254"),  # Fails snomed code min length
            ("INDICATION_CODE", "12321432543543543534"),  # Fails snomed code max length
            ("INDICATION_CODE", "18756hg098"),  # Fails regex
        ]

        for field, failing_value in test_cases:
            with self.subTest(field=field, failing_value=failing_value):
                invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
                invalid_batch_imms_payload[field] = failing_value

                validation_result = self.batch_dq_checker._check_validity(invalid_batch_imms_payload)

                self.assertEqual([field], validation_result)

    def test_check_validity_returns_list_of_multiple_invalid_fields_for_multiple_failures(self):
        invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
        invalid_batch_imms_payload["NHS_NUMBER"] = "12345678901"
        invalid_batch_imms_payload["EXPIRY_DATE"] = "20240137"
        invalid_batch_imms_payload["PERSON_POSTCODE"] = "12 ACX"
        invalid_batch_imms_payload["DOSE_AMOUNT"] = "6.789"
        invalid_batch_imms_payload["INDICATION_CODE"] = "123"

        validation_result = self.batch_dq_checker._check_validity(invalid_batch_imms_payload)

        self.assertEqual(
            ["NHS_NUMBER", "PERSON_POSTCODE", "EXPIRY_DATE", "DOSE_AMOUNT", "INDICATION_CODE"], validation_result
        )

    def test_check_timeliness_calculates_the_timeliness_diffs(self):
        timeliness_output = self.batch_dq_checker._check_timeliness(VALID_BATCH_IMMUNISATION, self.mock_fixed_datetime)

        self.assertEqual(4, timeliness_output.recorded_timeliness_days)
        self.assertEqual(785550, timeliness_output.ingested_timeliness_seconds)

    def test_check_timeliness_returns_none_for_recorded_timeliness_when_relevant_field_invalid(self):
        invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
        invalid_batch_imms_payload["RECORDED_DATE"] = ""

        timeliness_output = self.batch_dq_checker._check_timeliness(invalid_batch_imms_payload, self.mock_fixed_datetime)

        self.assertIsNone(timeliness_output.recorded_timeliness_days)
        self.assertEqual(785550, timeliness_output.ingested_timeliness_seconds)

    def test_check_timeliness_returns_none_for_both_when_date_and_time_field_invalid(self):
        invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
        invalid_batch_imms_payload["DATE_AND_TIME"] = "20245"

        timeliness_output = self.batch_dq_checker._check_timeliness(invalid_batch_imms_payload, self.mock_fixed_datetime)

        self.assertIsNone(timeliness_output.recorded_timeliness_days)
        self.assertIsNone(timeliness_output.ingested_timeliness_seconds)

    def test_run_checks_returns_correct_output_for_valid_data_for_csv_payload(self):
        result = self.batch_dq_checker.run_checks(VALID_BATCH_IMMUNISATION)
        self.assert_successful_result(result)

    def test_run_checks_returns_correct_output_for_valid_data_for_fhir_payload(self):
        result = self.fhir_json_dq_checker.run_checks(VALID_FHIR_IMMUNISATION)
        self.assert_successful_result(result)

    def test_run_checks_returns_correct_output_for_invalid_data_for_csv_payload(self):
        invalid_batch_imms_payload = copy.deepcopy(VALID_BATCH_IMMUNISATION)
        invalid_batch_imms_payload["NHS_NUMBER"] = "12345678901"
        invalid_batch_imms_payload["RECORDED_DATE"] = "20240137"
        invalid_batch_imms_payload["PERSON_DOB"] = ""
        invalid_batch_imms_payload["DOSE_AMOUNT"] = "6.789"
        invalid_batch_imms_payload["BATCH_NUMBER"] = ""

        result = self.batch_dq_checker.run_checks(invalid_batch_imms_payload)

        self.assertEqual([], result.missing_fields.optional_fields)
        self.assertEqual(["PERSON_DOB"], result.missing_fields.mandatory_fields)
        self.assertEqual(["BATCH_NUMBER"], result.missing_fields.required_fields)

        # Fields which are subject to validation and are also empty will appear in both the completeness and validity
        # checks e.g. PERSON_DOB
        self.assertEqual(["NHS_NUMBER", "PERSON_DOB", "DOSE_AMOUNT"], result.invalid_fields)
        self.assertIsNone(result.timeliness.recorded_timeliness_days)
        self.assertEqual(785550, result.timeliness.ingested_timeliness_seconds)

    def test_run_checks_returns_correct_output_for_invalid_data_for_fhir_payload(self):
        invalid_fhir_imms_payload = copy.deepcopy(VALID_FHIR_IMMUNISATION)
        invalid_fhir_imms_payload["contained"][1]["identifier"][0]["value"] = "12345678901"
        invalid_fhir_imms_payload["recorded"] = "2024-01-37"
        del invalid_fhir_imms_payload["contained"][1]["birthDate"]
        invalid_fhir_imms_payload["doseQuantity"]["value"] = "6.789"
        invalid_fhir_imms_payload["lotNumber"] = ""

        result = self.fhir_json_dq_checker.run_checks(invalid_fhir_imms_payload)

        self.assertEqual([], result.missing_fields.optional_fields)
        # Worth noting that due to the use of the fhir converter, invalid dates will be mapped to an empty string hence
        # will also show up here where they would not in batch validation
        self.assertEqual(["PERSON_DOB", "RECORDED_DATE"], result.missing_fields.mandatory_fields)
        self.assertEqual(["BATCH_NUMBER"], result.missing_fields.required_fields)

        # Fields which are subject to validation and are also empty will appear in both the completeness and validity
        # checks e.g. PERSON_DOB
        self.assertEqual(["NHS_NUMBER", "PERSON_DOB", "DOSE_AMOUNT"], result.invalid_fields)
        self.assertIsNone(result.timeliness.recorded_timeliness_days)
        self.assertEqual(785550, result.timeliness.ingested_timeliness_seconds)
