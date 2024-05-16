"""Tests for generic utils"""

import unittest

from src.models.utils.validation_utils import disease_codes_to_vaccine_type, get_vaccine_type
from src.mappings import VaccineTypes
from .utils.generic_utils import load_json_data


class TestGenericUtils(unittest.TestCase):
    """Tests for generic utils functions"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data(filename="completed_mmr_immunization_event.json")

    def test_disease_codes_to_vaccine_type(self):
        """
        Test that disease_codes_to_vaccine_type returns correct vaccine type for valid combinations,
        of disease codes, or raises a value error otherwise
        """
        # Valid combinations return appropriate vaccine type
        valid_combinations = [
            (["840539006"], VaccineTypes.covid_19),
            (["6142004"], VaccineTypes.flu),
            (["240532009"], VaccineTypes.hpv),
            (["14189004", "36989005", "36653000"], VaccineTypes.mmr),
            (["36989005", "14189004", "36653000"], VaccineTypes.mmr),
            (["36653000", "14189004", "36989005"], VaccineTypes.mmr),
        ]

        for combination, vaccine_type in valid_combinations:
            self.assertEqual(disease_codes_to_vaccine_type(combination), vaccine_type)

        # Invalid combinations raise value error
        invalid_combinations = [
            ["8405390063"],
            ["14189004"],
            ["14189004", "36989005"],
            ["14189004", "36989005", "36653000", "840539006"],
        ]

        for invalid_combination in invalid_combinations:
            with self.assertRaises(ValueError):
                disease_codes_to_vaccine_type(invalid_combination)

    def test_get_vaccine_type(self):
        """
        Test that get_vaccine_type returns the correct vaccine type when given valid json data with a
        valid combination of target disease code, or raises an error otherwise
        """
        vaccine_types = [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]
        for vaccine_type in vaccine_types:
            json_data = load_json_data(filename=f"completed_{vaccine_type.lower()}_immunization_event.json")
            self.assertEqual(get_vaccine_type(json_data), vaccine_type)

        # TODO: VACCINE_TYPE Test 'bad' data