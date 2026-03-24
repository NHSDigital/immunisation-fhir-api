"""Tests for generic utils"""

import datetime
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

from common.models.utils.generic_utils import (
    check_keys_in_sources,
    create_diagnostics,
    create_diagnostics_error,
    extract_file_key_elements,
    generate_field_location_for_name,
    get_contained_practitioner,
    get_nhs_number,
    get_occurrence_datetime,
    is_actor_referencing_contained_resource,
)
from common.models.utils.validation_utils import (
    convert_disease_codes_to_vaccine_type,
    get_vaccine_type,
)
from test_common.testing_utils.generic_utils import load_json_data, update_target_disease_code


class TestGenericUtils(unittest.TestCase):
    """Tests for generic utils functions"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data(filename="completed_mmr_immunization_event.json")
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("common.models.utils.validation_utils.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()

    def tearDown(self):
        """Tear down after each test. This runs after every test"""
        self.redis_getter_patcher.stop()

    def test_get_nhs_number_success(self):
        """Test get_nhs_number returns NHS number when present"""
        expected_nhs = "1234567890"
        imms = {"contained": [{"resourceType": "Patient", "identifier": [{"value": expected_nhs}]}]}
        result = get_nhs_number(imms)
        self.assertEqual(result, expected_nhs)

    def test_get_nhs_number_missing_patient(self):
        """Test get_nhs_number returns 'TBC' when patient not found"""
        imms = {"contained": []}
        result = get_nhs_number(imms)
        self.assertEqual(result, "TBC")

    def test_get_nhs_number_missing_identifier(self):
        """Test get_nhs_number returns 'TBC' when identifier not found"""
        imms = {"contained": [{"resourceType": "Patient"}]}
        result = get_nhs_number(imms)
        self.assertEqual(result, "TBC")

    def test_get_contained_practitioner(self):
        """Test get_contained_practitioner returns practitioner resource"""
        imms = {
            "contained": [
                {"resourceType": "Patient", "id": "patient1"},
                {"resourceType": "Practitioner", "id": "practitioner1"},
            ]
        }
        result = get_contained_practitioner(imms)
        self.assertEqual(result["id"], "practitioner1")

    def test_is_actor_referencing_contained_resource_true(self):
        """Test is_actor_referencing_contained_resource returns True for matching reference"""
        element = {"actor": {"reference": "#patient1"}}
        result = is_actor_referencing_contained_resource(element, "patient1")
        self.assertTrue(result)

    def test_is_actor_referencing_contained_resource_false(self):
        """Test is_actor_referencing_contained_resource returns False for non-matching reference"""
        element = {"actor": {"reference": "#patient2"}}
        result = is_actor_referencing_contained_resource(element, "patient1")
        self.assertFalse(result)

    def test_is_actor_referencing_contained_resource_missing_key(self):
        """Test is_actor_referencing_contained_resource returns False when keys missing"""
        element = {}
        result = is_actor_referencing_contained_resource(element, "patient1")
        self.assertFalse(result)

    def test_get_occurrence_datetime_valid(self):
        """Test get_occurrence_datetime returns datetime for valid occurrenceDateTime"""
        immunization = {"occurrenceDateTime": "2023-01-15T10:30:00Z"}
        result = get_occurrence_datetime(immunization)
        # The result will be timezone-aware due to the 'Z' in the ISO string
        expected = datetime.datetime(2023, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        self.assertEqual(result, expected)

    def test_get_occurrence_datetime_none(self):
        """Test get_occurrence_datetime returns None when occurrenceDateTime missing"""
        immunization = {}
        result = get_occurrence_datetime(immunization)
        self.assertIsNone(result)

    def test_create_diagnostics(self):
        """Test create_diagnostics returns expected error structure"""
        result = create_diagnostics()
        expected = {
            "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].value does not exists."
        }
        self.assertEqual(result, expected)

    def test_create_diagnostics_error_system(self):
        """Test create_diagnostics_error for system mismatch"""
        result = create_diagnostics_error("system")
        expected = {"diagnostics": "Validation errors: identifier[0].system doesn't match with the stored content"}
        self.assertEqual(result, expected)

    def test_create_diagnostics_error_value(self):
        """Test create_diagnostics_error for value mismatch"""
        result = create_diagnostics_error("value")
        expected = {"diagnostics": "Validation errors: identifier[0].value doesn't match with the stored content"}
        self.assertEqual(result, expected)

    def test_create_diagnostics_error_both(self):
        """Test create_diagnostics_error for both system and value mismatch"""
        result = create_diagnostics_error("Both")
        expected = {
            "diagnostics": "Validation errors: identifier[0].system and identifier[0].value doesn't match with the stored content"
        }
        self.assertEqual(result, expected)

    def test_check_keys_in_sources_query_params(self):
        """Test check_keys_in_sources with queryStringParameters"""
        event = {"queryStringParameters": {"key1": "value1", "key2": "value2"}}
        not_required_keys = ["key1"]
        result = check_keys_in_sources(event, not_required_keys)
        self.assertEqual(result, ["key1"])

    def test_check_keys_in_sources_body(self):
        """Test check_keys_in_sources with body content"""
        import base64

        body_data = "key1=value1&key2=value2"
        encoded_body = base64.b64encode(body_data.encode()).decode()
        event = {"body": encoded_body}
        not_required_keys = ["key1"]
        result = check_keys_in_sources(event, not_required_keys)
        self.assertEqual(result, ["key1"])

    def test_generate_field_location_for_name(self):
        """Test generate_field_location_for_name creates correct path"""
        result = generate_field_location_for_name("0", "given", "Patient")
        expected = "contained[?(@.resourceType=='Patient')].name[0].given"
        self.assertEqual(result, expected)

    def test_extract_file_key_elements(self):
        """Test extract_file_key_elements extracts vaccine type from file key"""
        file_key = "COVID_VACCINE_DATA.JSON"
        result = extract_file_key_elements(file_key)
        expected = {"vaccine_type": "COVID"}
        self.assertEqual(result, expected)

    def test_convert_disease_codes_to_vaccine_type_returns_vaccine_type(self):
        """
        If the mock returns a vaccine type, convert_disease_codes_to_vaccine_type returns that vaccine type.
        """
        valid_combinations = [
            (["840539006"], "COVID"),
            (["6142004"], "FLU"),
            (["240532009"], "HPV"),
            (["14189004", "36989005", "36653000"], "MMR"),
            (["36989005", "14189004", "36653000"], "MMR"),
            (["36653000", "14189004", "36989005"], "MMR"),
            (["55735004"], "RSV"),
        ]
        self.mock_redis.hget.side_effect = [
            "COVID",
            "FLU",
            "HPV",
            "MMR",
            "MMR",
            "MMR",
            "RSV",
        ]
        self.mock_redis_getter.return_value = self.mock_redis

        for combination, vaccine_type in valid_combinations:
            self.assertEqual(convert_disease_codes_to_vaccine_type(combination), vaccine_type)

    def test_convert_disease_codes_to_vaccine_type_raises_error_on_none(self):
        """
        If the mock returns None, convert_disease_codes_to_vaccine_type raises a ValueError.
        """
        invalid_combinations = [
            ["8405390063"],
            ["14189004"],
            ["14189004", "36989005"],
            ["14189004", "36989005", "36653000", "840539006"],
        ]
        self.mock_redis.hget.side_effect = None
        self.mock_redis.hget.return_value = None  # Simulate no match in Redis for invalid combinations
        self.mock_redis_getter.return_value = self.mock_redis
        for invalid_combination in invalid_combinations:
            with self.assertRaises(ValueError):
                convert_disease_codes_to_vaccine_type(invalid_combination)

    def test_get_vaccine_type(self):
        """
        Test that get_vaccine_type returns the correct vaccine type when given valid json data with a
        valid combination of target disease code, or raises an appropriate error otherwise
        """
        self.mock_redis.hget.return_value = "RSV"
        self.mock_redis_getter.return_value = self.mock_redis
        # TEST VALID DATA
        valid_json_data = load_json_data(filename="completed_rsv_immunization_event.json")

        vac_type = get_vaccine_type(valid_json_data)
        self.assertEqual(vac_type, "RSV")

        self.mock_redis.hget.return_value = "FLU"
        self.mock_redis_getter.return_value = self.mock_redis
        # VALID DATA: coding field with multiple coding systems including SNOMED
        flu_json_data = load_json_data(filename="completed_flu_immunization_event.json")
        valid_target_disease_element = {
            "coding": [
                {
                    "system": "ANOTHER_SYSTEM_URL",
                    "code": "ANOTHER_CODE",
                    "display": "Influenza",
                },
                {
                    "system": "http://snomed.info/sct",
                    "code": "6142004",
                    "display": "Influenza",
                },
            ]
        }
        flu_json_data["protocolApplied"][0]["targetDisease"][0] = valid_target_disease_element
        self.assertEqual(get_vaccine_type(flu_json_data), "FLU")

        # TEST INVALID DATA FOR SINGLE TARGET DISEASE
        self.mock_redis.hget.return_value = None  # Reset mock for invalid cases
        self.mock_redis_getter.return_value = self.mock_redis
        covid_json_data = load_json_data(filename="completed_covid_immunization_event.json")

        # INVALID DATA, SINGLE TARGET DISEASE: No targetDisease field
        invalid_covid_json_data = deepcopy(covid_json_data)
        del invalid_covid_json_data["protocolApplied"][0]["targetDisease"]
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_covid_json_data)
        self.assertEqual(
            str(error.exception),
            "Validation errors: protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"
            + " is a mandatory field",
        )

        invalid_target_disease_elements = [
            # INVALID DATA, SINGLE TARGET DISEASE: No "coding" field
            {"text": "Influenza"},
            # INVALID DATA, SINGLE TARGET DISEASE: Valid code, but no snomed coding system
            {
                "coding": [
                    {
                        "system": "NOT_THE_SNOMED_URL",
                        "code": "6142004",
                        "display": "Influenza",
                    }
                ]
            },
            # INVALID DATA, SINGLE TARGET DISEASE: coding field doesn't contain a code
            {"coding": [{"system": "http://snomed.info/sct", "display": "Influenza"}]},
        ]
        for invalid_target_disease in invalid_target_disease_elements:
            invalid_covid_json_data = deepcopy(covid_json_data)
            invalid_covid_json_data["protocolApplied"][0]["targetDisease"][0] = invalid_target_disease
            with self.assertRaises(ValueError) as error:
                get_vaccine_type(invalid_covid_json_data)
            self.assertEqual(
                str(error.exception),
                "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"
                + " is a mandatory field",
            )

        # INVALID DATA, SINGLE TARGET DISEASE: Invalid code
        invalid_covid_json_data = deepcopy(covid_json_data)
        update_target_disease_code(invalid_covid_json_data, "INVALID_CODE")
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_covid_json_data)
        self.assertEqual(
            str(error.exception),
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code"
            + " - ['INVALID_CODE'] is not a valid combination of disease codes for this service",
        )

        # TEST INVALID DATA FOR MULTIPLE TARGET DISEASES
        mmr_json_data = load_json_data(filename="completed_mmr_immunization_event.json")

        # INVALID DATA, MULTIPLE TARGET DISEASES: Invalid code combination
        invalid_mmr_json_data = deepcopy(mmr_json_data)
        # Change one of the target disease codes to the flu code so the combination of codes becomes invalid
        update_target_disease_code(invalid_mmr_json_data, "6142004")
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_mmr_json_data)
        self.assertEqual(
            str(error.exception),
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - "
            + "['6142004', '36989005', '36653000'] is not a valid combination of disease codes for this service",
        )

        # INVALID DATA, MULTIPLE TARGET DISEASES: One of the target disease elements does not have a coding field
        invalid_target_disease_elements = [
            # INVALID DATA, MULTIPLE TARGET DISEASES: No "coding" field
            {"text": "Mumps"},
            # INVALID DATA, MULTIPLE TARGET DISEASES: Valid code, but no snomed coding system
            {
                "coding": [
                    {
                        "system": "NOT_THE_SNOMED_URL",
                        "code": "36989005",
                        "display": "Mumps",
                    }
                ]
            },
            # INVALID DATA, MULTIPLE TARGET DISEASES: coding field doesn't contain a code
            {"coding": [{"system": "http://snomed.info/sct", "display": "Mumps"}]},
        ]
        for invalid_target_disease in invalid_target_disease_elements:
            invalid_mmr_json_data = deepcopy(mmr_json_data)
            invalid_mmr_json_data["protocolApplied"][0]["targetDisease"][1] = invalid_target_disease
            with self.assertRaises(ValueError) as error:
                get_vaccine_type(invalid_mmr_json_data)
            self.assertEqual(
                str(error.exception),
                "protocolApplied[0].targetDisease[1].coding[?(@.system=='http://snomed.info/sct')].code"
                + " is a mandatory field",
            )
