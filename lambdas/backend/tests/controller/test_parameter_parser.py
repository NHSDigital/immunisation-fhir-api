import unittest
from unittest.mock import Mock, create_autospec, patch

from controller.parameter_parser import (
    validate_and_retrieve_search_params,
)
from models.errors import ParameterExceptionError
from service.fhir_service import FhirService


class TestParameterParser(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.patient_identifier_key = "patient.identifier"
        self.immunization_target_key = "-immunization.target"
        self.date_from_key = "-date.from"
        self.date_to_key = "-date.to"
        self.include_key = "_include"
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("controller.parameter_parser.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_process_search_params_checks_patient_identifier_format(self):
        with self.assertRaises(ParameterExceptionError) as e:
            _ = validate_and_retrieve_search_params({self.patient_identifier_key: ["9000000009"]})
        self.assertEqual(
            str(e.exception),
            "patient.identifier must be in the format of "
            '"https://fhir.nhs.uk/Id/nhs-number|{NHS number}" '
            'e.g. "https://fhir.nhs.uk/Id/nhs-number|9000000009"',
        )
        self.mock_redis.hkeys.return_value = ["RSV"]
        self.mock_redis_getter.return_value = self.mock_redis
        validate_and_retrieve_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
            }
        )

    def test_process_search_params_whitelists_immunization_target(self):
        mock_redis_key = "RSV"
        self.mock_redis.hkeys.return_value = [mock_redis_key]
        self.mock_redis_getter.return_value = self.mock_redis

        with self.assertRaises(ParameterExceptionError) as e:
            validate_and_retrieve_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: [
                        "FLU",
                        "COVID",
                        "NOT-A-REAL-VALUE",
                    ],
                }
            )
        self.assertEqual(
            str(e.exception), f"-immunization.target must be one or more of the following: {mock_redis_key}"
        )

    def test_process_search_params_immunization_target(self):
        mock_redis_key = "RSV"
        self.mock_redis.hkeys.return_value = [mock_redis_key]
        self.mock_redis_getter.return_value = self.mock_redis
        params = validate_and_retrieve_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
            }
        )

        self.assertIsNotNone(params)

    def test_search_params_date_from_must_be_before_date_to(self):
        self.mock_redis.hkeys.return_value = ["RSV"]
        self.mock_redis_getter.return_value = self.mock_redis
        params = validate_and_retrieve_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
                self.date_from_key: ["2021-03-06"],
                self.date_to_key: ["2021-03-08"],
            }
        )

        self.assertIsNotNone(params)

        params = validate_and_retrieve_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
                self.date_from_key: ["2021-03-07"],
                self.date_to_key: ["2021-03-07"],
            }
        )

        self.assertIsNotNone(params)

        with self.assertRaises(ParameterExceptionError) as e:
            _ = validate_and_retrieve_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: ["RSV"],
                    self.date_from_key: ["2021-03-08"],
                    self.date_to_key: ["2021-03-07"],
                }
            )

        self.assertEqual(
            str(e.exception),
            f"Search parameter {self.date_from_key} must be before {self.date_to_key}",
        )

    def test_process_search_params_immunization_target_is_mandatory(self):
        self.mock_redis.hkeys.return_value = ["RSV"]
        self.mock_redis_getter.return_value = self.mock_redis
        with self.assertRaises(ParameterExceptionError) as e:
            _ = validate_and_retrieve_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                }
            )
        self.assertEqual(
            str(e.exception),
            "Search parameter -immunization.target must have one or more values.",
        )

    def test_process_search_params_patient_identifier_is_mandatory(self):
        with self.assertRaises(ParameterExceptionError) as e:
            _ = validate_and_retrieve_search_params(
                {
                    self.immunization_target_key: ["a-disease-type"],
                }
            )
        self.assertEqual(
            str(e.exception),
            "Search parameter patient.identifier must have one value.",
        )

    def test_process_search_params_dedupes_immunization_targets_and_respects_include(
        self,
    ):
        """Ensure duplicate immunization targets are deduped and include is preserved."""
        self.mock_redis.hkeys.return_value = ["RSV", "FLU"]
        self.mock_redis_getter.return_value = self.mock_redis

        params = validate_and_retrieve_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV", "RSV", "FLU"],
                "_include": ["immunization:patient"],
            }
        )

        # immunization targets should be deduped and preserve valid entries
        self.assertIsInstance(params.immunization_targets, set)
        self.assertCountEqual(params.immunization_targets, {"RSV", "FLU"})

        # include should be returned as provided
        self.assertEqual(params.include, "immunization:patient")

    def test_process_search_params_raises_date_errors(self):
        """When multiple date-related errors occur they should be returned together."""
        self.mock_redis.hkeys.return_value = ["RSV"]
        self.mock_redis_getter.return_value = self.mock_redis

        with self.assertRaises(ParameterExceptionError) as e:
            validate_and_retrieve_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: ["RSV"],
                    self.date_from_key: ["2021-01-01", "2021-01-02"],  # too many values
                    self.date_to_key: ["invalid-date"],  # invalid format
                }
            )
        expected = (
            f"Search parameter {self.date_from_key} may have one value at most.; "
            f"Search parameter {self.date_to_key} must be in format: YYYY-MM-DD"
        )
        self.assertEqual(str(e.exception), expected)

    def test_process_search_params_invalid_nhs_number_is_rejected(self):
        """If the NHS number fails mod11 check a ParameterException is raised."""
        # redis returns a valid vaccine type
        self.mock_redis.hkeys.return_value = ["RSV"]
        self.mock_redis_getter.return_value = self.mock_redis

        with self.assertRaises(ParameterExceptionError) as e:
            validate_and_retrieve_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|1234567890"],  # invalid mod11
                    self.immunization_target_key: ["RSV"],
                }
            )

        self.assertEqual(
            str(e.exception),
            f"Search parameter {self.patient_identifier_key} must be a valid NHS number.",
        )

    def test_process_search_params_invalid_include_value_is_rejected(self):
        """_include may only be 'Immunization:patient' if provided."""
        self.mock_redis.hkeys.return_value = ["RSV"]
        self.mock_redis_getter.return_value = self.mock_redis

        with self.assertRaises(ParameterExceptionError) as e:
            validate_and_retrieve_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: ["RSV"],
                    "_include": ["Patient:practitioner"],
                }
            )

        self.assertEqual(
            str(e.exception),
            f"Search parameter {self.include_key} may only be 'Immunization:patient' if provided.",
        )
