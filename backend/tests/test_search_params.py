import json

import base64

from mappings import VaccineTypes
from search_params import date_from_key, date_to_key


def test_process_params_is_sorted(self):
    lambda_event = {
        "multiValueQueryStringParameters": {
            self.patient_identifier_key: ["b,a"],
        },
        "body": base64.b64encode(f"{self.immunization_target_key}=b,a".encode("utf-8")),
        "headers": {'Content-Type': 'application/x-www-form-urlencoded'},
        "httpMethod": "POST"
    }
    processed_params = self.controller.process_params(lambda_event)

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
    processed_params = self.controller.process_params(lambda_event)

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

    with self.assertRaises(Exception) as e:
        self.controller.process_params(lambda_event)

    self.assertEqual(str(e.exception), "Parameters may not be duplicated. Use commas for \"or\".")


def test_process_search_params_checks_patient_identifier_format(self):
    params, errors = self.controller.process_search_params(
        {self.patient_identifier_key: ["9000000009"]}
    )
    self.assertEqual(errors, "patient.identifier must be in the format of "
                             "\"https://fhir.nhs.uk/Id/nhs-number|{NHS number}\" "
                             "e.g. \"https://fhir.nhs.uk/Id/nhs-number|9000000009\"")
    self.assertEqual(params, None)

    params, errors = self.controller.process_search_params(
        {
            self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
            self.immunization_target_key: [VaccineTypes().all[0]]
        }
    )

    self.assertEqual(errors, None)


def test_process_search_params_whitelists_immunization_target(self):
    params, errors = self.controller.process_search_params(
        {
            self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
            self.immunization_target_key: ["not-a-code"]
        }
    )
    self.assertEqual(errors, f"immunization-target must be one or more of the following: {','.join(VaccineTypes().all)}")
    self.assertIsNone(params)

    params, errors = self.controller.process_search_params(
        {
            self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
            self.immunization_target_key: [VaccineTypes().all[0]]
        }
    )

    self.assertIsNone(errors)
    self.assertIsNotNone(params)


def test_search_params_date_from_must_be_before_date_to(self):
    params, errors = self.controller.process_search_params(
        {
            self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
            self.immunization_target_key: [VaccineTypes().all[0]],
            self.date_from_key: ["2021-03-06"],
            self.date_to_key: ["2021-03-08"]
        }
    )

    self.assertIsNone(errors)
    self.assertIsNotNone(params)

    params, errors = self.controller.process_search_params(
        {
            self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
            self.immunization_target_key: [VaccineTypes().all[0]],
            self.date_from_key: ["2021-03-07"],
            self.date_to_key: ["2021-03-07"]
        }
    )

    self.assertIsNone(errors)
    self.assertIsNotNone(params)

    params, errors = self.controller.process_search_params(
        {
            self.patient_identifier_key: ["https://fhir.nhs.uk/Id/nhs-number|9000000009"],
            self.immunization_target_key: [VaccineTypes().all[0]],
            self.date_from_key: ["2021-03-08"],
            self.date_to_key: ["2021-03-07"]
        }
    )

    self.assertEqual(errors, f"Search parameter {date_from_key} must be before {date_to_key}")
    self.assertIsNone(params)


def test_diseaseType_is_mandatory(self):
    """diseaseType is a mandatory query param"""
    lambda_event = {"multiValueQueryStringParameters": {
        self.patient_identifier_key: ["an-id"],
    }}

    response = self.controller.search_immunizations(lambda_event)

    self.assertEqual(self.service.search_immunizations.call_count, 0)
    self.assertEqual(response["statusCode"], 400)
    outcome = json.loads(response["body"])
    self.assertEqual(outcome["resourceType"], "OperationOutcome")