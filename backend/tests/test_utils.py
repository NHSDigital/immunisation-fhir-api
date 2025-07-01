"""Tests for generic utils"""

import unittest
import json
from unittest.mock import patch, MagicMock
from copy import deepcopy
from sample_data.mock_redis_cache import fake_hget

from models.utils.validation_utils import convert_disease_codes_to_vaccine_type, get_vaccine_type
from utils.generic_utils import load_json_data, update_target_disease_code


class TestGenericUtils(unittest.TestCase):
    """Tests for generic utils functions"""
    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data(filename="completed_mmr_immunization_event.json")
        self.redis_patcher = patch("models.utils.validation_utils.redis_client")
        self.mock_redis_client = self.redis_patcher.start()
        self.mock_redis_client.hget.side_effect = fake_hget

    def tearDown(self):
        """Tear down after each test. This runs after every test"""
        self.redis_patcher.stop()

    def test_convert_disease_codes_to_vaccine_type(self):
        """
        Test that disease_codes_to_vaccine_type returns correct vaccine type for valid combinations,
        of disease codes, or raises a value error otherwise
        """
        # Valid combinations return appropriate vaccine type
        valid_combinations = [
            (["840539006"], "COVID19"),
            (["6142004"], "FLU"),
            (["240532009"], "HPV"),
            (["14189004", "36989005", "36653000"], "MMR"),
            (["36989005", "14189004", "36653000"], "MMR"),
            (["36653000", "14189004", "36989005"], "MMR"),
            (["55735004"], "RSV")
        ]

        for combination, vaccine_type in valid_combinations:
            self.assertEqual(convert_disease_codes_to_vaccine_type(combination), vaccine_type)

        # Invalid combinations raise value error
        invalid_combinations = [
            ["8405390063"],
            ["14189004"],
            ["14189004", "36989005"],
            ["14189004", "36989005", "36653000", "840539006"],
        ]

        for invalid_combination in invalid_combinations:
            with self.assertRaises(ValueError):
                convert_disease_codes_to_vaccine_type(invalid_combination)

    def test_get_vaccine_type(self):
        """
        Test that get_vaccine_type returns the correct vaccine type when given valid json data with a
        valid combination of target disease code, or raises an appropriate error otherwise
        """
        # TEST VALID DATA
        valid_json_data = load_json_data(filename=f"completed_rsv_immunization_event.json")
        # print(valid_json_data)
        vac_type = get_vaccine_type(valid_json_data)
        self.assertEqual(vac_type, "RSV")

        # VALID DATA: coding field with multiple coding systems including SNOMED
        flu_json_data = load_json_data(filename=f"completed_flu_immunization_event.json")
        valid_target_disease_element = {
            "coding": [
                {"system": "ANOTHER_SYSTEM_URL", "code": "ANOTHER_CODE", "display": "Influenza"},
                {"system": "http://snomed.info/sct", "code": "6142004", "display": "Influenza"},
            ]
        }
        flu_json_data["protocolApplied"][0]["targetDisease"][0] = valid_target_disease_element
        self.assertEqual(get_vaccine_type(flu_json_data), "FLU")

        # TEST INVALID DATA FOR SINGLE TARGET DISEASE
        covid_19_json_data = load_json_data(
            filename=f"completed_covid19_immunization_event.json"
        )

        # INVALID DATA, SINGLE TARGET DISEASE: No targetDisease field
        invalid_covid_19_json_data = deepcopy(covid_19_json_data)
        del invalid_covid_19_json_data["protocolApplied"][0]["targetDisease"]
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_covid_19_json_data)
        self.assertEqual(
            str(error.exception),
            "Validation errors: protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"
            + " is a mandatory field",
        )

        invalid_target_disease_elements = [
            # INVALID DATA, SINGLE TARGET DISEASE: No "coding" field
            {"text": "Influenza"},
            # INVALID DATA, SINGLE TARGET DISEASE: Valid code, but no snomed coding system
            {"coding": [{"system": "NOT_THE_SNOMED_URL", "code": "6142004", "display": "Influenza"}]},
            # INVALID DATA, SINGLE TARGET DISEASE: coding field doesn't contain a code
            {"coding": [{"system": "http://snomed.info/sct", "display": "Influenza"}]},
        ]
        for invalid_target_disease in invalid_target_disease_elements:
            invalid_covid_19_json_data = deepcopy(covid_19_json_data)
            invalid_covid_19_json_data["protocolApplied"][0]["targetDisease"][0] = invalid_target_disease
            with self.assertRaises(ValueError) as error:
                get_vaccine_type(invalid_covid_19_json_data)
            self.assertEqual(
                str(error.exception),
                "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"
                + " is a mandatory field",
            )

        # INVALID DATA, SINGLE TARGET DISEASE: Invalid code
        invalid_covid_19_json_data = deepcopy(covid_19_json_data)
        update_target_disease_code(invalid_covid_19_json_data, "INVALID_CODE")
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_covid_19_json_data)
        self.assertEqual(
            str(error.exception),
            "Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code"
            + " - ['INVALID_CODE'] is not a valid combination of disease codes for this service",
        )

        # TEST INVALID DATA FOR MULTIPLE TARGET DISEASES
        mmr_json_data = load_json_data(filename=f"completed_mmr_immunization_event.json")

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
            {"coding": [{"system": "NOT_THE_SNOMED_URL", "code": "36989005", "display": "Mumps"}]},
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
