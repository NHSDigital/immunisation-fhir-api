import base64
import datetime
import unittest
from unittest.mock import create_autospec, patch

from models.errors import ParameterException
from parameter_parser import (
    SearchParams,
    create_query_string,
    date_from_key,
    date_to_key,
    include_key,
    process_params,
    process_search_params,
)
from service.fhir_service import FhirService


class TestParameterParser(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.patient_identifier_key = "patient.identifier"
        self.immunization_target_key = "-immunization.target"
        self.date_from_key = "-date.from"
        self.date_to_key = "-date.to"
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.redis_patcher = patch("parameter_parser.redis_client")
        self.mock_redis_client = self.redis_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_process_params_combines_content_and_query_string(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["a"],
            },
            "body": base64.b64encode(f"{self.immunization_target_key}=b".encode("utf-8")),
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "httpMethod": "POST",
        }

        processed_params = process_params(lambda_event)

        expected = {
            self.patient_identifier_key: ["a"],
            self.immunization_target_key: ["b"],
        }

        self.assertEqual(expected, processed_params)

    def test_process_params_is_sorted(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["b,a"],
            },
            "body": base64.b64encode(f"{self.immunization_target_key}=b,a".encode("utf-8")),
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "httpMethod": "POST",
        }
        processed_params = process_params(lambda_event)

        for v in processed_params.values():
            self.assertEqual(sorted(v), v)

    def test_process_params_does_not_process_body_on_get(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["b,a"],
            },
            "body": base64.b64encode(
                f"{self.immunization_target_key}=b&{self.immunization_target_key}=a".encode("utf-8")
            ),
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "httpMethod": "GET",
        }
        processed_params = process_params(lambda_event)

        self.assertEqual(processed_params, {self.patient_identifier_key: ["a", "b"]})

    def test_process_params_does_not_allow_anded_params(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["a,b"],
                self.immunization_target_key: ["a", "b"],
            },
            "body": None,
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "httpMethod": "POST",
        }

        with self.assertRaises(ParameterException) as e:
            process_params(lambda_event)

        self.assertEqual(str(e.exception), 'Parameters may not be duplicated. Use commas for "or".')

    def test_process_search_params_checks_patient_identifier_format(self):
        with self.assertRaises(ParameterException) as e:
            _ = process_search_params({self.patient_identifier_key: ["9000000009"]})
        self.assertEqual(
            str(e.exception),
            "patient.identifier must be in the format of "
            '"https://fhir.nhs.uk/Id/nhs-number|{NHS number}" '
            'e.g. "https://fhir.nhs.uk/Id/nhs-number|9000000009"',
        )
        self.mock_redis_client.hkeys.return_value = ["RSV"]
        process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
            }
        )

    def test_process_search_params_whitelists_immunization_target(self):
        mock_redis_key = "RSV"
        self.mock_redis_client.hkeys.return_value = [mock_redis_key]
        with self.assertRaises(ParameterException) as e:
            process_search_params(
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
            str(e.exception),
            f"immunization-target must be one or more of the following: {mock_redis_key}",
            f"Unexpected exception message: {str(e.exception)}",
        )

    def test_process_search_params_immunization_target(self):
        mock_redis_key = "RSV"
        self.mock_redis_client.hkeys.return_value = [mock_redis_key]
        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
            }
        )

        self.assertIsNotNone(params)

    def test_search_params_date_from_must_be_before_date_to(self):
        self.mock_redis_client.hkeys.return_value = ["RSV"]
        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
                self.date_from_key: ["2021-03-06"],
                self.date_to_key: ["2021-03-08"],
            }
        )

        self.assertIsNotNone(params)

        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV"],
                self.date_from_key: ["2021-03-07"],
                self.date_to_key: ["2021-03-07"],
            }
        )

        self.assertIsNotNone(params)

        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: ["RSV"],
                    self.date_from_key: ["2021-03-08"],
                    self.date_to_key: ["2021-03-07"],
                }
            )

        self.assertEqual(
            str(e.exception),
            f"Search parameter {date_from_key} must be before {date_to_key}",
        )

    def test_process_search_params_immunization_target_is_mandatory(self):
        self.mock_redis_client.hkeys.return_value = ["RSV"]
        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                }
            )
        self.assertEqual(
            str(e.exception),
            "Search parameter -immunization.target must have one or more values.",
        )

    def test_process_search_params_patient_identifier_is_mandatory(self):
        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {
                    self.immunization_target_key: ["a-disease-type"],
                }
            )
        self.assertEqual(
            str(e.exception),
            "Search parameter patient.identifier must have one value.",
        )

    def test_create_query_string_with_all_params(self):
        search_params = SearchParams("a", ["b"], datetime.date(1, 2, 3), datetime.date(4, 5, 6), "c")
        query_string = create_query_string(search_params)
        expected = (
            "-date.from=0001-02-03&-date.to=0004-05-06&-immunization.target=b"
            "&_include=c&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7Ca"
        )

        self.assertEqual(expected, query_string)

    def test_create_query_string_with_minimal_params(self):
        search_params = SearchParams("a", ["b"], None, None, None)
        query_string = create_query_string(search_params)
        expected = "-immunization.target=b&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7Ca"

        self.assertEqual(expected, query_string)

    def test_create_query_string_with_multiple_immunization_targets_comma_separated(
        self,
    ):
        search_params = SearchParams("a", ["b", "c"], None, None, None)
        query_string = create_query_string(search_params)
        expected = "-immunization.target=b,c&patient.identifier=https%3A%2F%2Ffhir.nhs.uk%2FId%2Fnhs-number%7Ca"

        self.assertEqual(expected, query_string)

    def test_process_search_params_dedupes_immunization_targets_and_respects_include(
        self,
    ):
        """Ensure duplicate immunization targets are deduped and include is preserved."""
        self.mock_redis_client.hkeys.return_value = ["RSV", "FLU"]

        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: ["RSV", "RSV", "FLU"],
                "_include": ["immunization:patient"],
            }
        )

        # immunization targets should be deduped and preserve valid entries
        self.assertIsInstance(params.immunization_targets, list)
        self.assertCountEqual(params.immunization_targets, ["RSV", "FLU"])

        # include should be returned as provided
        self.assertEqual(params.include, "immunization:patient")

    def test_process_search_params_aggregates_date_errors(self):
        """When multiple date-related errors occur they should be returned together."""
        self.mock_redis_client.hkeys.return_value = ["RSV"]

        with self.assertRaises(ParameterException) as e:
            process_search_params(
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
        self.mock_redis_client.hkeys.return_value = ["RSV"]

        with self.assertRaises(ParameterException) as e:
            process_search_params(
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
        self.mock_redis_client.hkeys.return_value = ["RSV"]

        with self.assertRaises(ParameterException) as e:
            process_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: ["RSV"],
                    "_include": ["Patient:practitioner"],
                }
            )

        self.assertEqual(
            str(e.exception),
            f"Search parameter {include_key} may only be 'Immunization:patient' if provided.",
        )
