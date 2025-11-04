import json
import unittest
from unittest.mock import patch

from exceptions.id_sync_exception import IdSyncException
from record_processor import process_record


class TestRecordProcessor(unittest.TestCase):
    DEFAULT_DEMOGRAPHIC_DATA = {
        "name": [{"given": ["John"], "family": "Doe"}],
        "gender": "male",
        "birthDate": "1980-01-01",
    }

    def setUp(self):
        """Set up test fixtures and mocks"""
        # Patch logger
        self.logger_patcher = patch("record_processor.logger")
        self.mock_logger = self.logger_patcher.start()

        # PDS helpers
        self.pds_get_patient_details_patcher = patch("record_processor.pds_get_patient_details")
        self.mock_pds_get_patient_details = self.pds_get_patient_details_patcher.start()

        self.ieds_update_patient_id_patcher = patch("record_processor.ieds_update_patient_id")
        self.mock_ieds_update_patient_id = self.ieds_update_patient_id_patcher.start()

        self.get_items_from_patient_id_patcher = patch("record_processor.get_items_from_patient_id")
        self.mock_get_items_from_patient_id = self.get_items_from_patient_id_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_process_record_success_no_update_required(self):
        """Test successful processing when patient ID matches"""
        # Arrange
        test_id = "54321"
        # Simulate IEDS items exist
        self.mock_get_items_from_patient_id.return_value = [{"Resource": {}}]
        test_record = {"body": json.dumps({"subject": test_id})}
        self.mock_pds_get_patient_details.return_value = {
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": test_id,
                }
            ]
        }

        # Act
        result = process_record(test_record)

        # Assert
        self.assertEqual(result["message"], "No update required")
        self.assertEqual(result["status"], "success")

        # Verify calls
        self.mock_pds_get_patient_details.assert_called_once_with(test_id)

    def test_process_record_success_update_required(self):
        """Test successful processing when patient ID differs and demographics match"""
        # Arrange
        pds_id = "9000000008"
        nhs_number = "9000000009"

        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}

        # pds_get_patient_details should return details used by demographics_match
        self.mock_pds_get_patient_details.return_value = {
            **self.DEFAULT_DEMOGRAPHIC_DATA,
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": pds_id,
                }
            ],
        }

        # Provide one IEDS item that will match demographics via demographics_match
        matching_item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Patient",
                        "id": "Pat1",
                        "name": [{"given": ["John"], "family": "Doe"}],
                        "gender": "male",
                        "birthDate": "1980-01-01",
                    }
                ],
            }
        }
        self.mock_get_items_from_patient_id.return_value = [matching_item]

        success_response = {"status": "success"}
        self.mock_ieds_update_patient_id.return_value = success_response

        # Act
        result = process_record(test_sqs_record)

        # Assert
        self.assertEqual(result, success_response)
        self.mock_pds_get_patient_details.assert_called_once_with(nhs_number)

    def test_process_record_demographics_mismatch_skips_update(self):
        """If no IEDS item matches demographics, the update should be skipped"""
        # Arrange
        pds_id = "pds-1"
        nhs_number = "nhs-1"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}

        self.mock_pds_get_patient_details.return_value = {
            "name": [{"given": ["Alice"], "family": "Smith"}],
            "gender": "female",
            "birthDate": "1995-05-05",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": pds_id,
                }
            ],
        }

        # IEDS items exist but do not match demographics
        non_matching_item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Patient",
                        "id": "Pat2",
                        "name": [{"given": ["Bob"], "family": "Jones"}],
                        "gender": "male",
                        "birthDate": "1990-01-01",
                    }
                ],
            }
        }
        self.mock_get_items_from_patient_id.return_value = [non_matching_item]

        # Act
        result = process_record(test_sqs_record)

        # Assert
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records matched PDS demographics; update skipped")

    def test_invalid_body_parsing_returns_error(self):
        """When body is a malformed string, process_record should return an error"""
        bad_record = {"body": "not-a-json-or-python-literal"}
        result = process_record(bad_record)
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid body format", result["message"])

    def test_no_subject_in_body_returns_error(self):
        """When body doesn't contain a subject, return an error"""
        result = process_record({"body": json.dumps({"other": "value"})})
        self.assertEqual(result["status"], "error")
        self.assertIn("No NHS number found", result["message"])

    def test_pds_details_exception_aborts_update(self):
        """If fetching PDS details raises, function should return error"""
        nhs_number = "nhs-exc-1"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}
        # pds returns a different id to force update path
        self.mock_get_items_from_patient_id.return_value = [{"Resource": {}}]
        self.mock_pds_get_patient_details.side_effect = IdSyncException("Error retrieving patient details from PDS")

        result = process_record(test_sqs_record)
        self.assertEqual(result["status"], "error")
        self.assertIn("Error retrieving patient details from PDS", result["message"])

    def test_get_items_exception_aborts_update(self):
        """If fetching IEDS items raises, function should return error"""
        nhs_number = "nhs-exc-2"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}
        self.mock_get_items_from_patient_id.return_value = [{"Resource": {}}]
        self.mock_pds_get_patient_details.return_value = {
            "name": [{"given": ["J"], "family": "K"}],
            "gender": "male",
            "birthDate": "2000-01-01",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "1234",
                }
            ],
        }
        self.mock_get_items_from_patient_id.side_effect = Exception("dynamo fail")

        result = process_record(test_sqs_record)
        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to fetch IEDS items", result["message"])

    def test_update_called_on_match(self):
        """Verify ieds_update_patient_id is called when demographics match"""
        pds_id = "pds-match"
        nhs_number = "nhs-match"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}
        self.mock_pds_get_patient_details.return_value = {
            "name": [{"given": ["Sarah"], "family": "Fowley"}],
            "gender": "male",
            "birthDate": "1956-07-09",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": pds_id,
                }
            ],
        }
        item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Patient",
                        "id": "PatM",
                        "name": [{"given": ["Sarah"], "family": "Fowley"}],
                        "gender": "male",
                        "birthDate": "1956-07-09",
                    }
                ],
            }
        }
        self.mock_get_items_from_patient_id.return_value = [item]
        self.mock_ieds_update_patient_id.return_value = {"status": "success"}

        result = process_record(test_sqs_record)
        self.assertEqual(result["status"], "success")
        self.mock_ieds_update_patient_id.assert_called_once_with(nhs_number, pds_id, items_to_update=[item])

    def test_process_record_no_records_exist(self):
        """Test when no records exist for the patient ID"""
        # Arrange
        test_id = "12345"
        # Simulate no IEDS items
        self.mock_get_items_from_patient_id.return_value = []
        test_record = {"body": json.dumps({"subject": test_id})}

        # Act
        result = process_record(test_record)

        self.assertEqual(result["message"], "No records returned for NHS Number")

        # Verify PDS was not called
        self.mock_pds_get_patient_details.assert_called_once()

    def test_process_record_pds_returns_none_id(self):
        """Test when PDS returns none"""
        # Arrange
        test_id = "12345a"
        self.mock_pds_get_patient_details.return_value = None
        test_record = {"body": json.dumps({"subject": test_id})}

        # Act & Assert
        result = process_record(test_record)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No patient ID found for NHS number")
        # No IEDS lookups should have been attempted when PDS returns None
        self.mock_get_items_from_patient_id.assert_not_called()
        self.mock_ieds_update_patient_id.assert_not_called()

    def test_process_record_ieds_returns_false(self):
        """Test when id doesnt exist in IEDS"""
        # Arrange
        test_id = "12345a"
        pds_id = "pds-id-1"
        self.mock_pds_get_patient_details.return_value = {
            "name": [{"given": ["Sarah"], "family": "Fowley"}],
            "gender": "male",
            "birthDate": "1956-07-09",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": pds_id,
                }
            ],
        }
        # Simulate no items returned from IEDS
        self.mock_get_items_from_patient_id.return_value = []

        # Act & Assert
        result = process_record({"body": json.dumps({"subject": test_id})})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records returned for NHS Number")

    def test_process_record_returns_failure_when_json_invalid(self):
        """Test that a failure status is returned when invalid JSON is provided from the MNS service. In reality,
        unlikely from this external NHS service."""
        result = process_record({"body": '{"key_one": "not enclosed'})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Invalid body format")

    def test_body_is_string_json(self):
        """Test processing a simple record"""
        # Arrange
        test_record = {"body": '{"subject": "nhs-number-1"}'}
        new_test_id = "nhs-number-2"

        self.mock_pds_get_patient_details.return_value = {
            "name": [{"given": ["A"], "family": "B"}],
            "gender": "female",
            "birthDate": "1990-01-01",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": new_test_id,
                }
            ],
        }
        self.mock_get_items_from_patient_id.return_value = [
            {
                "Resource": {
                    "resourceType": "Immunization",
                    "contained": [
                        {
                            "resourceType": "Patient",
                            "id": "Pat3",
                            "name": [{"given": ["A"], "family": "B"}],
                            "gender": "female",
                            "birthDate": "1990-01-01",
                        }
                    ],
                }
            }
        ]
        self.mock_ieds_update_patient_id.return_value = {"status": "success"}
        # Act
        result = process_record(test_record)

        # Assert
        self.assertEqual(result["status"], "success")

    def test_process_record_birthdate_mismatch_skips_update(self):
        """If birthDate differs between PDS and IEDS, update should be skipped"""
        pds_id = "pds-2"
        nhs_number = "nhs-2"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}

        self.mock_pds_get_patient_details.return_value = {
            **self.DEFAULT_DEMOGRAPHIC_DATA,
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": pds_id,
                }
            ],
        }

        # IEDS has different birthDate
        item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Patient",
                        "id": "PatX",
                        "name": [{"given": ["John"], "family": "Doe"}],
                        "gender": "male",
                        "birthDate": "1980-01-02",
                    }
                ],
            }
        }
        self.mock_get_items_from_patient_id.return_value = [item]

        result = process_record(test_sqs_record)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records matched PDS demographics; update skipped")

    def test_process_record_gender_mismatch_skips_update(self):
        """If gender differs between PDS and IEDS, update should be skipped"""
        pds_id = "pds-3"
        nhs_number = "nhs-3"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}

        self.mock_pds_get_patient_details.return_value = {
            "name": [{"given": ["Alex"], "family": "Smith"}],
            "gender": "female",
            "birthDate": "1992-03-03",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": pds_id,
                }
            ],
        }

        # IEDS has different gender
        item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Patient",
                        "id": "PatY",
                        "name": [{"given": ["Alex"], "family": "Smith"}],
                        "gender": "male",
                        "birthDate": "1992-03-03",
                    }
                ],
            }
        }
        self.mock_get_items_from_patient_id.return_value = [item]

        result = process_record(test_sqs_record)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records matched PDS demographics; update skipped")

    def test_process_record_no_comparable_fields_skips_update(self):
        """If PDS provides no comparable fields, do not update (skip)"""
        nhs_number = "nhs-4"
        test_sqs_record = {"body": json.dumps({"subject": nhs_number})}

        # PDS returns minimal/empty details
        self.mock_pds_get_patient_details.return_value = {
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "123456789012",
                }
            ]
        }

        item = {
            "Resource": {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Patient",
                        "id": "PatZ",
                        "name": [{"given": ["Zoe"], "family": "Lee"}],
                        "gender": "female",
                        "birthDate": "2000-01-01",
                    }
                ],
            }
        }
        self.mock_get_items_from_patient_id.return_value = [item]

        result = process_record(test_sqs_record)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "No records matched PDS demographics; update skipped")
