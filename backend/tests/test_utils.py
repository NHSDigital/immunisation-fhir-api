"""Tests for generic utils"""

import unittest
from copy import deepcopy

from src.models.utils.validation_utils import convert_disease_codes_to_vaccine_type, get_vaccine_type
from src.mappings import VaccineTypes, DiseaseCodes
from .utils.generic_utils import load_json_data, update_target_disease_code


class TestGenericUtils(unittest.TestCase):
    """Tests for generic utils functions"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data(filename="completed_mmr_immunization_event.json")

    def test_convert_disease_codes_to_vaccine_type(self):
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
        vaccine_types = [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr]
        for vaccine_type in vaccine_types:
            valid_json_data = load_json_data(filename=f"completed_{vaccine_type.lower()}_immunization_event.json")
            self.assertEqual(get_vaccine_type(valid_json_data), vaccine_type)

        # VALID DATA: coding field with multiple coding systems including SNOMED
        flu_json_data = load_json_data(filename=f"completed_{VaccineTypes.flu.lower()}_immunization_event.json")
        valid_target_disease_element = {
            "coding": [
                {"system": "ANOTHER_SYSTEM_URL", "code": "ANOTHER_CODE", "display": "Influenza"},
                {"system": "http://snomed.info/sct", "code": f"{DiseaseCodes.flu}", "display": "Influenza"},
            ]
        }
        flu_json_data["protocolApplied"][0]["targetDisease"][0] = valid_target_disease_element
        self.assertEqual(get_vaccine_type(flu_json_data), VaccineTypes.flu)

        # TEST INVALID DATA FOR SINGLE TARGET DISEASE
        covid_19_json_data = load_json_data(
            filename=f"completed_{VaccineTypes.covid_19.lower()}_immunization_event.json"
        )

        # INVALID DATA, SINGLE TARGET DISEASE: No targetDisease field
        invalid_covid_19_json_data = deepcopy(covid_19_json_data)
        del invalid_covid_19_json_data["protocolApplied"][0]["targetDisease"]
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_covid_19_json_data)
        self.assertEqual(
            str(error.exception),
            "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code"
            + " is a mandatory field",
        )

        invalid_target_disease_elements = [
            # INVALID DATA, SINGLE TARGET DISEASE: No "coding" field
            {"text": "Influenza"},
            # INVALID DATA, SINGLE TARGET DISEASE: Valid code, but no snomed coding system
            {"coding": [{"system": "NOT_THE_SNOMED_URL", "code": f"{DiseaseCodes.flu}", "display": "Influenza"}]},
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
            "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code"
            + " - ['INVALID_CODE'] is not a valid combination of disease codes for this service",
        )

        # TEST INVALID DATA FOR MULTIPLE TARGET DISEASES
        mmr_json_data = load_json_data(filename=f"completed_{VaccineTypes.mmr.lower()}_immunization_event.json")

        # INVALID DATA, MULTIPLE TARGET DISEASES: Invalid code combination
        invalid_mmr_json_data = deepcopy(mmr_json_data)
        # Change one of the target disease codes to the flu code so the combination of codes becomes invalid
        update_target_disease_code(invalid_mmr_json_data, DiseaseCodes.flu)
        with self.assertRaises(ValueError) as error:
            get_vaccine_type(invalid_mmr_json_data)
        self.assertEqual(
            str(error.exception),
            "protocolApplied[0].targetDisease[*].coding[?(@.system=='http://snomed.info/sct')].code - "
            + f"['{DiseaseCodes.flu}', '36989005', '36653000'] is not a valid combination of disease codes for this "
            + "service",
        )

        # INVALID DATA, MULTIPLE TARGET DISEASES: One of the target disease elements does not have a coding field
        invalid_mmr_json_data = deepcopy(mmr_json_data)
        invalid_target_disease_elements = [
            # INVALID DATA, MULTIPLE TARGET DISEASES: No "coding" field
            {"text": "Mumps"},
            # INVALID DATA, MULTIPLE TARGET DISEASES: Valid code, but no snomed coding system
            {"coding": [{"system": "NOT_THE_SNOMED_URL", "code": f"{DiseaseCodes.mumps}", "display": "Influenza"}]},
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
