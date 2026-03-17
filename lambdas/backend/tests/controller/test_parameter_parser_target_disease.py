import unittest
from unittest.mock import Mock, patch

from controller.constants import ImmunizationSearchParameterName
from controller.parameter_parser import (
    validate_and_retrieve_search_params_by_disease,
    validate_search_param_mutual_exclusivity,
)
from models.errors import ParameterExceptionError


class TestTargetDiseaseSearch(unittest.TestCase):
    def setUp(self):
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("controller.parameter_parser.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()
        self.mock_redis_getter.return_value = self.mock_redis
        self.patient_id = "https://fhir.nhs.uk/Id/nhs-number|9000000009"
        self.snomed_system = "http://snomed.info/sct"

    def tearDown(self):
        patch.stopall()

    def test_validate_search_param_mutual_exclusivity_raises_when_target_disease_with_immunization_target(self):
        with self.assertRaises(ParameterExceptionError) as e:
            validate_search_param_mutual_exclusivity(
                {
                    ImmunizationSearchParameterName.TARGET_DISEASE: [f"{self.snomed_system}|14189004"],
                    ImmunizationSearchParameterName.IMMUNIZATION_TARGET: ["MMR"],
                    ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
                }
            )
        self.assertIn("cannot be used with", str(e.exception))
        self.assertIn("target-disease", str(e.exception))

    def test_validate_search_param_mutual_exclusivity_raises_when_target_disease_with_identifier(self):
        with self.assertRaises(ParameterExceptionError) as e:
            validate_search_param_mutual_exclusivity(
                {
                    ImmunizationSearchParameterName.TARGET_DISEASE: [f"{self.snomed_system}|14189004"],
                    "identifier": ["http://example.org|abc-123"],
                    ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
                }
            )
        self.assertIn("cannot be used with", str(e.exception))

    def test_validate_search_param_mutual_exclusivity_passes_when_only_target_disease_and_patient(self):
        validate_search_param_mutual_exclusivity(
            {
                ImmunizationSearchParameterName.TARGET_DISEASE: [f"{self.snomed_system}|14189004"],
                ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
            }
        )

    def test_validate_and_retrieve_search_params_by_disease_returns_vaccine_types_from_cache(self):
        self.mock_redis.hget.return_value = '["14189004", "840539006"]'
        self.mock_redis.hgetall.return_value = {"14189004": '["MMR", "MMRV"]'}
        result = validate_and_retrieve_search_params_by_disease(
            {
                ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
                ImmunizationSearchParameterName.TARGET_DISEASE: [f"{self.snomed_system}|14189004"],
            }
        )
        self.assertCountEqual(result.params.immunization_targets, {"MMR", "MMRV"})
        self.assertIsNotNone(result.params.target_disease_codes_for_url)
        self.assertIn(f"{self.snomed_system}|14189004", result.params.target_disease_codes_for_url)
        self.assertFalse(result.no_mapped_target_diseases_provided)

    def test_validate_and_retrieve_search_params_by_disease_requires_patient_identifier(self):
        self.mock_redis.hget.return_value = '["14189004"]'
        self.mock_redis.hgetall.return_value = {"14189004": '["MMR"]'}
        with self.assertRaises(ParameterExceptionError):
            validate_and_retrieve_search_params_by_disease(
                {
                    ImmunizationSearchParameterName.TARGET_DISEASE: [f"{self.snomed_system}|14189004"],
                }
            )

    def test_validate_and_retrieve_search_params_by_disease_raises_when_all_format_invalid(self):
        self.mock_redis.hget.return_value = "[]"
        self.mock_redis.hgetall.return_value = {}
        with self.assertRaises(ParameterExceptionError) as e:
            validate_and_retrieve_search_params_by_disease(
                {
                    ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
                    ImmunizationSearchParameterName.TARGET_DISEASE: ["invalid-no-pipe", "wrong_system|123"],
                }
            )
        self.assertIn("target-disease", str(e.exception))

    def test_validate_and_retrieve_search_params_by_disease_raises_when_target_disease_empty(self):
        with self.assertRaises(ParameterExceptionError) as e:
            validate_and_retrieve_search_params_by_disease(
                {
                    ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
                    ImmunizationSearchParameterName.TARGET_DISEASE: [],
                }
            )
        self.assertIn("must have one or more values", str(e.exception))

    def test_validate_and_retrieve_search_params_by_disease_returns_all_not_in_mapping_when_target_disease_list_cache_missing(
        self,
    ):
        self.mock_redis.hget.return_value = None
        self.mock_redis.hgetall.return_value = {}
        result = validate_and_retrieve_search_params_by_disease(
            {
                ImmunizationSearchParameterName.PATIENT_IDENTIFIER: [self.patient_id],
                ImmunizationSearchParameterName.TARGET_DISEASE: [f"{self.snomed_system}|14189004"],
            }
        )
        self.assertTrue(result.no_mapped_target_diseases_provided)
        self.assertEqual(result.params.immunization_targets, set())
        self.assertIsNotNone(result.params.target_disease_codes_for_url)
        self.assertIn(f"{self.snomed_system}|14189004", result.params.target_disease_codes_for_url)
        self.assertEqual(len(result.invalid_target_diseases), 1)
        self.assertIn("14189004", result.invalid_target_diseases[0])
