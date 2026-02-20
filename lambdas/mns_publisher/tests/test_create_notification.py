import copy
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from constants import IMMUNISATION_TYPE, SPEC_VERSION
from create_notification import (
    calculate_age_at_vaccination,
    create_mns_notification,
    get_practitioner_details_from_pds,
)


class TestCalculateAgeAtVaccination(unittest.TestCase):
    """Tests for age calculation at vaccination time."""

    def test_age_calculation_yyyymmdd_format(self):
        """Test age calculation with YYYYMMDD format."""
        birth_date = "20040609"
        vaccination_date = "20260212"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 21)

    def test_age_calculation_with_time(self):
        """Test age calculation with YYYYMMDDTHHmmss format."""
        birth_date = "20040609T120000"
        vaccination_date = "20260212T174437"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 21)

    def test_age_calculation_after_birthday(self):
        """Test age when vaccination is after birthday."""
        birth_date = "20040609"
        vaccination_date = "20260815"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 22)

    def test_age_calculation_on_birthday(self):
        """Test age when vaccination is on birthday."""
        birth_date = "20040609"
        vaccination_date = "20260609"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 22)

    def test_age_calculation_infant(self):
        """Test age calculation for infant (less than 1 year old)."""
        birth_date = "20260609"
        vaccination_date = "20260915"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 0)

    def test_age_calculation_leap_year_birthday(self):
        """Test age calculation with leap year birthday."""
        birth_date = "20000229"
        vaccination_date = "20240228"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 23)

    def test_age_calculation_same_day_different_year(self):
        """Test age calculation for same day in different year."""
        birth_date = "20000101"
        vaccination_date = "20250101"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 25)


class TestGetPractitionerDetailsFromPds(unittest.TestCase):
    """Tests for get_practitioner_details_from_pds function."""

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_success(self, mock_logger, mock_pds_get):
        """Test successful retrieval of GP ODS code."""
        mock_pds_get.return_value = {"generalPractitioner": {"value": "Y12345"}}

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
        mock_logger.warning.assert_called_once_with("No patient details found for NHS number")

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
        """Test when value field is missing from generalPractitioner."""
        mock_pds_get.return_value = {"generalPractitioner": {"system": "https://fhir.nhs.uk"}}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_with("GP ODS code not found in practitioner details")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_empty_value(self, mock_logger, mock_pds_get):
        """Test when value is empty string."""
        mock_pds_get.return_value = {"generalPractitioner": {"value": ""}}

        result = get_practitioner_details_from_pds("9481152782")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_with("GP ODS code not found in practitioner details")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_pds_exception(self, mock_logger, mock_pds_get):
        """Test when PDS API raises exception."""
        mock_pds_get.side_effect = Exception("PDS API error")

        with self.assertRaises(Exception) as context:
            get_practitioner_details_from_pds("9481152782")

        self.assertEqual(str(context.exception), "PDS API error")
        mock_logger.exception.assert_called_once()

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.logger")
    def test_get_practitioner_patient_details_none(self, mock_logger, mock_pds_get):
        """Test when pds_get_patient_details returns None."""
        mock_pds_get.return_value = None

        with self.assertRaises(AttributeError):
            get_practitioner_details_from_pds("9481152782")


class TestCreateMnsNotification(unittest.TestCase):
    """Tests for MNS notification creation."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        sample_event_path = Path(__file__).parent.parent / "tests" / "sqs_event.json"
        with open(sample_event_path, "r") as f:
            raw_event = json.load(f)

        # Convert body from dict to JSON string (as it would be in real SQS)
        if isinstance(raw_event.get("body"), dict):
            raw_event["body"] = json.dumps(raw_event["body"])
            cls.sample_sqs_event = raw_event

    def setUp(self):
        """Set up test fixtures."""
        self.expected_gp_ods_code = "Y12345"
        self.expected_immunisation_url = "https://int.api.service.nhs.uk/immunisation-fhir-api"

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    @patch("create_notification.uuid.uuid4")
    def test_create_mns_notification_success_with_real_payload(self, mock_uuid, mock_get_service_url, mock_get_gp):
        """Test successful MNS notification creation using real SQS event."""
        mock_uuid.return_value = MagicMock(hex="236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b")
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        self.assertEqual(result["specversion"], SPEC_VERSION)
        self.assertEqual(result["type"], IMMUNISATION_TYPE)
        self.assertEqual(result["source"], self.expected_immunisation_url)
        self.assertEqual(result["subject"], "9481152782")
        self.assertIn("id", result)
        self.assertIn("time", result)
        self.assertIn("dataref", result)
        self.assertIn("filtering", result)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_dataref_format_real_payload(self, mock_get_service_url, mock_get_gp):
        """Test dataref URL format is correct with real payload."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        expected_dataref = f"{self.expected_immunisation_url}/Immunization/d058014c-b0fd-4471-8db9-3316175eb825"
        self.assertEqual(result["dataref"], expected_dataref)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_filtering_fields_real_payload(self, mock_get_service_url, mock_get_gp):
        """Test all filtering fields are populated correctly with real payload."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        filtering = result["filtering"]
        self.assertEqual(filtering["generalpractitioner"], self.expected_gp_ods_code)
        self.assertEqual(filtering["sourceorganisation"], "B0C4P")
        self.assertEqual(filtering["sourceapplication"], "TPP")
        self.assertEqual(filtering["immunisationtype"], "hib")
        self.assertEqual(filtering["action"], "CREATE")
        self.assertIsInstance(filtering["subjectage"], str)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_age_calculation_real_payload(self, mock_get_service_url, mock_get_gp):
        """Test patient age is calculated correctly with real payload."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        self.assertEqual(result["filtering"]["subjectage"], "21")

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_calls_get_practitioner_real_payload(self, mock_get_service_url, mock_get_gp):
        """Test get_practitioner_details_from_pds is called with correct NHS number from real payload."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        create_mns_notification(self.sample_sqs_event)

        mock_get_gp.assert_called_once_with("9481152782")

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_uuid_generated(self, mock_get_service_url, mock_get_gp):
        """Test unique ID is generated for each notification."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result1 = create_mns_notification(self.sample_sqs_event)
        result2 = create_mns_notification(self.sample_sqs_event)

        self.assertNotEqual(result1["id"], result2["id"])

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_invalid_json_body(self, mock_get_service_url, mock_get_gp):
        """Test error handling when SQS body is invalid JSON."""
        mock_get_service_url.return_value = self.expected_immunisation_url

        invalid_event = {"messageId": "test-id", "body": "not valid json {"}

        with self.assertRaises(json.JSONDecodeError):
            create_mns_notification(invalid_event)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_pds_failure(self, mock_get_service_url, mock_get_gp):
        """Test handling when get_practitioner_details_from_pds call fails."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.side_effect = Exception("PDS API unavailable")

        with self.assertRaises(Exception):
            create_mns_notification(self.sample_sqs_event)

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_gp_not_found(self, mock_get_service_url, mock_get_gp):
        """Test handling when GP ODS code is not found (returns None)."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = None

        result = create_mns_notification(self.sample_sqs_event)

        self.assertIsNone(result["filtering"]["generalpractitioner"])

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_required_fields_present(self, mock_get_service_url, mock_get_gp):
        """Test all required CloudEvents fields are present."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        required_fields = ["id", "source", "specversion", "type", "time", "dataref", "subject"]
        for field in required_fields:
            self.assertIn(field, result, f"Required field '{field}' missing")

    @patch("create_notification.get_practitioner_details_from_pds")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_missing_imms_data_field(self, mock_get_service_url, mock_get_gp):
        """Test handling when a required field is missing from imms_data."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_get_gp.return_value = self.expected_gp_ods_code

        incomplete_event = {
            "messageId": "test-id",
            "body": json.dumps({"dynamodb": {"NewImage": {"ImmsID": {"S": "test-id"}}}}),
        }

        with self.assertRaises((KeyError, TypeError)):
            create_mns_notification(incomplete_event)


@patch("create_notification.get_practitioner_details_from_pds")
@patch("create_notification.get_service_url")
def test_create_mns_notification_with_update_action(self, mock_get_service_url, mock_get_gp):
    """Test notification creation with UPDATE action using real payload structure."""
    mock_get_service_url.return_value = self.expected_immunisation_url
    mock_get_gp.return_value = self.expected_gp_ods_code

    update_event = copy.deepcopy(self.sample_sqs_event)

    update_event["body"]["dynamodb"]["NewImage"]["Operation"]["S"] = "UPDATE"

    result = create_mns_notification(update_event)

    self.assertEqual(result["filtering"]["action"], "UPDATE")
    mock_get_service_url.assert_called()
    mock_get_gp.assert_called()


if __name__ == "__main__":
    unittest.main()
