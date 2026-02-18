import json
import unittest
from unittest.mock import MagicMock, patch

from constants import IMMUNISATION_TYPE, SPEC_VERSION
from create_notification import calculate_age_at_vaccination, create_mns_notification


class TestCalculateAgeAtVaccination(unittest.TestCase):
    """Tests for age calculation at vaccination time."""

    def test_age_calculation_yyyymmdd_format(self):
        """Test age calculation with YYYYMMDD format (actual format from payload)."""
        birth_date = "20040609"
        vaccination_date = "20260212"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 21)  # Before birthday

    def test_age_calculation_with_time(self):
        """Test age calculation with YYYYMMDDTHHmmss format."""
        birth_date = "20040609T120000"
        vaccination_date = "20260212T174437"

        age = calculate_age_at_vaccination(birth_date, vaccination_date)

        self.assertEqual(age, 21)

    def test_age_calculation_after_birthday(self):
        """Test age when vaccination is after birthday."""
        birth_date = "20040609"
        vaccination_date = "20260815"  # After June 9th

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


class TestCreateMnsNotification(unittest.TestCase):
    """Tests for MNS notification creation."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_sqs_event = {
            "messageId": "98ed30eb-829f-41df-8a73-57fef70cf161",
            "body": json.dumps(
                {
                    "eventID": "b1ba2a48eae68bf43a8cb49b400788c6",
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "ImmsID": {"S": "d058014c-b0fd-4471-8db9-3316175eb825"},
                            "VaccineType": {"S": "hib"},
                            "SupplierSystem": {"S": "TPP"},
                            "DateTimeStamp": {"S": "2026-02-12T17:45:37+00:00"},
                            "Imms": {
                                "M": {
                                    "NHS_NUMBER": {"S": "9481152782"},
                                    "PERSON_DOB": {"S": "20040609"},
                                    "DATE_AND_TIME": {"S": "20260212T174437"},
                                    "VACCINE_TYPE": {"S": "hib"},
                                    "SITE_CODE": {"S": "B0C4P"},
                                }
                            },
                            "Operation": {"S": "CREATE"},
                        }
                    },
                }
            ),
        }

        self.expected_gp_ods_code = "Y12345"
        self.expected_immunisation_url = "https://int.api.service.nhs.uk/immunisation-fhir-api"

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    @patch("create_notification.uuid.uuid4")
    def test_create_mns_notification_success(self, mock_uuid, mock_get_service_url, mock_pds):
        """Test successful MNS notification creation."""
        # Setup mocks
        mock_uuid.return_value = MagicMock(hex="236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b")
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        # Execute
        result = create_mns_notification(self.sample_sqs_event)

        # Verify structure
        self.assertEqual(result["specversion"], SPEC_VERSION)
        self.assertEqual(result["type"], IMMUNISATION_TYPE)
        self.assertEqual(result["source"], self.expected_immunisation_url)
        self.assertEqual(result["subject"], "9481152782")
        self.assertIn("id", result)
        self.assertIn("time", result)
        self.assertIn("dataref", result)
        self.assertIn("filtering", result)

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_dataref_format(self, mock_get_service_url, mock_pds):
        """Test dataref URL format is correct."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        expected_dataref = f"{self.expected_immunisation_url}/Immunization/d058014c-b0fd-4471-8db9-3316175eb825"
        self.assertEqual(result["dataref"], expected_dataref)

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_filtering_fields(self, mock_get_service_url, mock_pds):
        """Test all filtering fields are populated correctly."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        filtering = result["filtering"]
        self.assertEqual(filtering["generalpractitioner"], self.expected_gp_ods_code)
        self.assertEqual(filtering["sourceorganisation"], "B0C4P")
        self.assertEqual(filtering["sourceapplication"], "TPP")
        self.assertEqual(filtering["immunisationtype"], "hib")
        self.assertEqual(filtering["action"], "CREATE")
        self.assertIsInstance(filtering["subjectage"], str)

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_age_calculation(self, mock_get_service_url, mock_pds):
        """Test patient age is calculated correctly."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        # Birth: 2004-06-09, Vaccination: 2026-02-12
        # Expected age: 21 (before birthday in 2026)
        self.assertEqual(result["filtering"]["subjectage"], "21")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_calls_pds(self, mock_get_service_url, mock_pds):
        """Test PDS is called with correct NHS number."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        create_mns_notification(self.sample_sqs_event)

        mock_pds.assert_called_once_with("9481152782")

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_uuid_generated(self, mock_get_service_url, mock_pds):
        """Test unique ID is generated for each notification."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        result1 = create_mns_notification(self.sample_sqs_event)
        result2 = create_mns_notification(self.sample_sqs_event)

        # Each notification should have a different ID
        self.assertNotEqual(result1["id"], result2["id"])

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_invalid_json_body(self, mock_get_service_url, mock_pds):
        """Test error handling when SQS body is invalid JSON."""
        mock_get_service_url.return_value = self.expected_immunisation_url

        invalid_event = {"messageId": "test-id", "body": "not valid json {"}

        with self.assertRaises(json.JSONDecodeError):
            create_mns_notification(invalid_event)

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_pds_failure(self, mock_get_service_url, mock_pds):
        """Test handling when PDS call fails."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.side_effect = Exception("PDS API unavailable")

        with self.assertRaises(Exception):
            create_mns_notification(self.sample_sqs_event)

    @patch("create_notification.pds_get_patient_details")
    @patch("create_notification.get_service_url")
    def test_create_mns_notification_required_fields_present(self, mock_get_service_url, mock_pds):
        """Test all required CloudEvents fields are present."""
        mock_get_service_url.return_value = self.expected_immunisation_url
        mock_pds.return_value = self.expected_gp_ods_code

        result = create_mns_notification(self.sample_sqs_event)

        required_fields = ["id", "source", "specversion", "type", "time", "dataref"]
        for field in required_fields:
            self.assertIn(field, result, f"Required field '{field}' missing")


if __name__ == "__main__":
    unittest.main()
