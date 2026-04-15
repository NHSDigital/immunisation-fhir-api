import copy
import json
import unittest
from unittest.mock import MagicMock, patch

from constants import IMMUNISATION_EVENT_SOURCE, IMMUNISATION_EVENT_TYPE, SPEC_VERSION
from create_notification import (
    calculate_age_at_vaccination,
    create_mns_notification,
    get_practitioner_details_from_pds,
)
from test_utils import load_sample_sqs_event


class TestCalculateAgeAtVaccination(unittest.TestCase):
    """Tests for age calculation at vaccination time."""

    def test_age_calculation_core_cases(self):
        cases = [
            ("20040609", "20260212", 21),  # YYYYMMDD format
            ("20040609", "20260609", 22),  # On birthday
            ("20040609", "20260815", 22),  # After birthday
            ("20260609", "20260915", 0),  # Infant
            ("20040609T120000", "20260212T17443700", 21),  # With time
            ("20000101", "20250101", 25),  # Same day different year
            ("20000229", "20240228", 23),  # Leap year birthday
            ("20000229", "20240229", 24),  # Leap year birthday on leap day
            ("20000229", "20250228", 24),  # day before; birthday hasn't happened yet
        ]

        for birth_date, vaccination_date, expected_age in cases:
            with self.subTest(birth_date=birth_date, vaccination_date=vaccination_date):
                self.assertEqual(
                    calculate_age_at_vaccination(birth_date, vaccination_date),
                    expected_age,
                )

    def test_rejects_invalid_birth_date_format(self):
        with self.assertRaisesRegex(ValueError, "PERSON_DOB"):
            calculate_age_at_vaccination("2004-06-09", "20260212")

    def test_rejects_invalid_vaccination_date_format(self):
        with self.assertRaisesRegex(ValueError, "DATE_AND_TIME"):
            calculate_age_at_vaccination("20040609", "2026-02-12")

    def test_rejects_nonexistent_birth_date(self):
        with self.assertRaisesRegex(ValueError, "PERSON_DOB"):
            calculate_age_at_vaccination("20040230", "20260212")


class TestCreateMnsNotification(unittest.TestCase):
    """Tests for MNS notification creation."""

    @classmethod
    def setUpClass(cls):
        cls.sample_sqs_event = load_sample_sqs_event()

    def setUp(self):
        self.expected_gp_ods_code = "Y12345"
        self.expected_immunisation_url = "https://int.api.service.nhs.uk/immunisation-fhir-api"

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    @patch("create_notification.uuid.uuid4")
    def test_success_create_mns_notification_complete_payload(self, mock_uuid, mock_get_service_url, mock_get_gp):
        mock_uuid.return_value = MagicMock(hex="236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b")
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        self.assertEqual(result["specversion"], SPEC_VERSION)
        self.assertEqual(result["type"], IMMUNISATION_EVENT_TYPE)
        self.assertEqual(result["source"], IMMUNISATION_EVENT_SOURCE)
        self.assertEqual(result["subject"], "9481152782")

        expected_dataref = f"{self.expected_immunisation_url}/Immunization/d058014c-b0fd-4471-8db9-3316175eb825"
        self.assertEqual(result["dataref"], expected_dataref)

        filtering = result["filtering"]
        self.assertEqual(filtering["generalpractitioner"], self.expected_gp_ods_code)
        self.assertEqual(filtering["sourceorganisation"], "B0C4P")
        self.assertEqual(filtering["sourceapplication"], "TPP")
        self.assertEqual(filtering["immunisationtype"], "HIB")
        self.assertEqual(filtering["action"], "CREATE")
        self.assertEqual(filtering["subjectage"], 21)

        self.assertIn("id", result)
        self.assertIsInstance(result["id"], str)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_missing_nhs_number(self, mock_get_service_url, mock_get_gp):
        sqs_event_data = copy.deepcopy(self.sample_sqs_event)

        body = json.loads(sqs_event_data["body"])
        body["dynamodb"]["NewImage"]["Imms"]["M"]["NHS_NUMBER"]["S"] = ""
        sqs_event_data["body"] = json.dumps(body)

        with self.assertRaises(ValueError) as context:
            create_mns_notification(sqs_event_data)
        self.assertIn("NHS number is required", str(context.exception))

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_calls_get_practitioner_real_payload(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        create_mns_notification(self.sample_sqs_event)

        mock_get_gp.assert_called_once_with("9481152782")

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_invalid_json_body(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        invalid_event = {"messageId": "test-id", "body": "not valid json {"}

        with self.assertRaises(json.JSONDecodeError):
            create_mns_notification(invalid_event)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_pds_failure(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.side_effect = Exception("PDS API unavailable")

        with self.assertRaises(Exception):
            create_mns_notification(self.sample_sqs_event)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_gp_not_found(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = None

        result = create_mns_notification(self.sample_sqs_event)

        self.assertIsNone(result["filtering"]["generalpractitioner"])

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_required_fields_present(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        required_fields = ["id", "source", "specversion", "type", "time", "dataref", "subject"]
        for field in required_fields:
            self.assertIn(field, result, f"Required field '{field}' missing")

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_missing_imms_data_field(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        incomplete_event = {
            "messageId": "test-id",
            "body": json.dumps({"dynamodb": {"NewImage": {"ImmsID": {"S": "test-id"}}}}),
        }

        with self.assertRaises((KeyError, TypeError, ValueError)):
            create_mns_notification(incomplete_event)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_with_update_action(self, mock_get_service_url, mock_get_gp):
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        update_event = copy.deepcopy(self.sample_sqs_event)

        body = json.loads(update_event["body"])
        body["dynamodb"]["NewImage"]["Operation"]["S"] = "UPDATE"
        update_event["body"] = json.dumps(body)

        result = create_mns_notification(update_event)

        self.assertEqual(result["filtering"]["action"], "UPDATE")
        mock_get_service_url.assert_called()
        mock_get_gp.assert_called()


class TestGetPractitionerDetailsFromPds(unittest.TestCase):
    """Tests for get_practitioner_details_from_pds function."""

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_success(self, mock_logger, mock_pds_get):
        """Test successful retrieval of GP ODS code."""
        mock_pds_get.return_value = {"generalPractitioner": [{"identifier": {"value": "Y12345"}}]}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertEqual(result, "Y12345")
        mock_pds_get.assert_called_once_with("9481152782")
        mock_logger.warning.assert_not_called()

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_no_gp_details(self, mock_logger, mock_pds_get):
        """Test when generalPractitioner is missing."""
        mock_pds_get.return_value = {"name": "John Doe"}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_once_with("No GP details found for patient")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_gp_is_none(self, mock_logger, mock_pds_get):
        """Test when generalPractitioner is None."""
        mock_pds_get.return_value = {"generalPractitioner": None}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_once()

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_no_value_field(self, mock_logger, mock_pds_get):
        """Test when value field is missing from identifier."""
        mock_pds_get.return_value = {"generalPractitioner": [{"identifier": {}}]}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_with("GP ODS code not found in practitioner details")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_empty_value(self, mock_logger, mock_pds_get):
        """Test when value is empty string."""
        mock_pds_get.return_value = {"generalPractitioner": [{"identifier": {"value": ""}}]}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_with("GP ODS code not found in practitioner details")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_no_end_date(self, mock_logger, mock_pds_get):
        """Test successful retrieval when no end date (current registration)."""
        mock_pds_get.return_value = {
            "generalPractitioner": [{"identifier": {"value": "Y12345", "period": {"start": "2024-01-01"}}}]
        }

        result = get_practitioner_details_from_pds("9481152782")

        self.assertEqual(result, "Y12345")
        mock_logger.warning.assert_not_called()

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_future_end_date(self, mock_logger, mock_pds_get):
        """Test successful retrieval when end date is in the future."""
        mock_pds_get.return_value = {
            "generalPractitioner": [
                {"identifier": {"value": "Y12345", "period": {"start": "2024-01-01", "end": "2030-12-31"}}}
            ]
        }

        result = get_practitioner_details_from_pds("9481152782")

        self.assertEqual(result, "Y12345")
        mock_logger.warning.assert_not_called()

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_expired_registration(self, mock_logger, mock_pds_get):
        """Test when GP registration has ended (expired)."""
        mock_pds_get.return_value = {
            "generalPractitioner": [
                {"identifier": {"value": "Y12345", "period": {"start": "2020-01-01", "end": "2023-12-31"}}}
            ]
        }

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_with("No current GP registration found for patient")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_no_period_field(self, mock_logger, mock_pds_get):
        """Test when period field is missing entirely."""
        mock_pds_get.return_value = {"generalPractitioner": [{"identifier": {"value": "Y12345"}}]}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertEqual(result, "Y12345")
        mock_logger.warning.assert_not_called()

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_pds_exception(self, mock_logger, mock_pds_get):
        """Test when PDS API raises exception."""
        mock_pds_get.side_effect = Exception("PDS API error")

        with self.assertRaises(Exception) as context:
            get_practitioner_details_from_pds("9481152782")

        self.assertEqual(str(context.exception), "PDS API error")
