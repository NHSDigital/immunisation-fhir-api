import base64
import unittest
from unittest.mock import create_autospec

from authorization import Authorization
from fhir_service import FhirService
from mappings import VaccineTypes
from models.errors import ParameterException
from parameter_parser import date_from_key, date_to_key, process_params, process_search_params


class TestParameterParser(unittest.TestCase):
    def setUp(self):
        self.service = create_autospec(FhirService)
        self.authorizer = create_autospec(Authorization)
        self.patient_identifier_key = "patient.identifier"
        self.immunization_target_key = "-immunization.target"
        self.date_from_key = "-date.from"
        self.date_to_key = "-date.to"

    def test_process_params_combines_content_and_query_string(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["a"],
            },
            "body": base64.b64encode(f"{self.immunization_target_key}=b".encode("utf-8")),
            "headers": {'Content-Type': 'application/x-www-form-urlencoded'},
            "httpMethod": "POST"
        }

        processed_params = process_params(lambda_event)

        expected = {
            self.patient_identifier_key: ["a"],
            self.immunization_target_key: ["b"]
        }

        self.assertEqual(expected, processed_params)

    def test_process_params_is_sorted(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["b,a"],
            },
            "body": base64.b64encode(f"{self.immunization_target_key}=b,a".encode("utf-8")),
            "headers": {'Content-Type': 'application/x-www-form-urlencoded'},
            "httpMethod": "POST"
        }
        processed_params = process_params(lambda_event)

        for (k, v) in processed_params.items():
            self.assertEqual(sorted(v), v)

    def test_process_params_does_not_process_body_on_get(self):
        lambda_event = {
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: ["b,a"],
            },
            "body": base64.b64encode(f"{self.immunization_target_key}=b&{self.immunization_target_key}=a".encode("utf-8")),
            "headers": {'Content-Type': 'application/x-www-form-urlencoded'},
            "httpMethod": "GET"
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
            "headers": {'Content-Type': 'application/x-www-form-urlencoded'},
            "httpMethod": "POST"
        }

        with self.assertRaises(ParameterException) as e:
            process_params(lambda_event)

        self.assertEqual(str(e.exception), "Parameters may not be duplicated. Use commas for \"or\".")

    def test_process_search_params_checks_patient_identifier_format(self):
        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {self.patient_identifier_key: ["9000000009"]}
            )
        self.assertEqual(str(e.exception), "patient.identifier must be in the format of "
                                 "\"https://fhir.nhs.uk/Id/nhs-number|{NHS number}\" "
                                 "e.g. \"https://fhir.nhs.uk/Id/nhs-number|9000000009\"")

        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: [VaccineTypes().all[0]]
            }
        )
        self.assertIsNotNone(params)

    def test_process_search_params_whitelists_immunization_target(self):
        with self.assertRaises(ParameterException) as e:
            process_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: ["not-a-code"]
                }
            )
        self.assertEqual(str(e.exception),
                         f"immunization-target must be one or more of the following: {','.join(VaccineTypes().all)}")

        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: [VaccineTypes().all[0]]
            }
        )

        self.assertIsNotNone(params)

    def test_search_params_date_from_must_be_before_date_to(self):
        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: [VaccineTypes().all[0]],
                self.date_from_key: ["2021-03-06"],
                self.date_to_key: ["2021-03-08"]
            }
        )

        self.assertIsNotNone(params)

        params = process_search_params(
            {
                self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                self.immunization_target_key: [VaccineTypes().all[0]],
                self.date_from_key: ["2021-03-07"],
                self.date_to_key: ["2021-03-07"]
            }
        )

        self.assertIsNotNone(params)

        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                    self.immunization_target_key: [VaccineTypes().all[0]],
                    self.date_from_key: ["2021-03-08"],
                    self.date_to_key: ["2021-03-07"]
                }
            )

        self.assertEqual(str(e.exception), f"Search parameter {date_from_key} must be before {date_to_key}")

    def test_process_search_params_immunization_target_is_mandatory(self):
        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {
                    self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
                }
            )
        self.assertEqual(str(e.exception), f"Search parameter -immunization.target must have one or more values.")

    def test_process_search_params_patient_identifier_is_mandatory(self):
        with self.assertRaises(ParameterException) as e:
            _ = process_search_params(
                {
                    self.immunization_target_key: ["a-disease-type"],
                }
            )
        self.assertEqual(str(e.exception), f"Search parameter patient.identifier must have one or more values.")
