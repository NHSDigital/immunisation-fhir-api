import base64
import datetime
import json
import unittest
import urllib.parse
from unittest.mock import Mock, create_autospec, patch

from fhir.resources.R4B.bundle import Bundle, BundleEntry, BundleLink
from fhir.resources.R4B.immunization import Immunization

from controller.fhir_controller import FhirController
from controller.parameter_parser import PATIENT_IDENTIFIER_SYSTEM
from service.fhir_service import FhirService


class TestSearchImmunizationsByTargetDisease(unittest.TestCase):
    """Automation tests for search using target-disease parameter."""

    patient_identifier_key = "patient.identifier"
    target_disease_key = "target-disease"
    immunization_target_key = "-immunization.target"
    nhs_number_valid_value = "9000000009"
    patient_identifier_valid_value = f"{PATIENT_IDENTIFIER_SYSTEM}|{nhs_number_valid_value}"
    snomed_system = "http://snomed.info/sct"
    measles_code = "14189004"

    def setUp(self):
        super().setUp()
        self.mock_redis = Mock()
        self.redis_getter_patcher = patch("controller.parameter_parser.get_redis_client")
        self.mock_redis_getter = self.redis_getter_patcher.start()
        self.mock_redis_getter.return_value = self.mock_redis
        self.service = create_autospec(FhirService)
        self.controller = FhirController(self.service)
        self.mock_redis.hgetall.return_value = {self.measles_code: json.dumps(["MMR", "MMRV"])}

    def tearDown(self):
        self.redis_getter_patcher.stop()

    def _hget_target_disease_codes_and_mmr(self, key, field):
        if field == "codes":
            return json.dumps([self.measles_code, "840539006"])
        return None

    def test_search_by_target_disease_is_successful(self):
        """it should search by target-disease and call service with resolved vaccine types and target_disease_codes_for_url"""
        self.mock_redis.hget.side_effect = self._hget_target_disease_codes_and_mmr
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "imms-1"}))],
            link=[BundleLink.construct(relation="self", url="search-url")],
            type="searchset",
            total=1,
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code}"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 200)
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value,
            {"MMR", "MMRV"},
            "test",
            None,
            None,
            None,
            None,
            {f"{self.snomed_system}|{self.measles_code}"},
            [],
        )
        self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.assert_not_called()

    def test_search_by_target_disease_successful_via_post(self):
        """it should support target-disease search via POST _search endpoint"""
        self.mock_redis.hget.side_effect = self._hget_target_disease_codes_and_mmr
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[],
            link=[BundleLink.construct(relation="self", url="search-url")],
            type="searchset",
            total=0,
        )
        form_data = {
            self.patient_identifier_key: self.patient_identifier_valid_value,
            self.target_disease_key: f"{self.snomed_system}|{self.measles_code}",
        }
        lambda_event = {
            "headers": {"Content-Type": "application/x-www-form-urlencoded", "SupplierSystem": "test"},
            "multiValueQueryStringParameters": {},
            "body": base64.b64encode(urllib.parse.urlencode(form_data).encode("utf-8")).decode("utf-8"),
        }

        response = self.controller.search_immunizations(lambda_event, is_post_endpoint_req=True)

        self.assertEqual(response["statusCode"], 200)
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value,
            {"MMR", "MMRV"},
            "test",
            None,
            None,
            None,
            None,
            {f"{self.snomed_system}|{self.measles_code}"},
            [],
        )

    def test_search_returns_400_when_target_disease_with_immunization_target(self):
        """it should return 400 when target-disease is used together with -immunization.target"""
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code}"],
                self.immunization_target_key: ["COVID"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("cannot be used with", json.loads(response["body"])["issue"][0]["diagnostics"])
        self.assertIn("target-disease", json.loads(response["body"])["issue"][0]["diagnostics"])
        self.service.search_immunizations.assert_not_called()
        self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.assert_not_called()

    def test_search_returns_400_when_target_disease_with_identifier(self):
        """it should return 400 when target-disease is used together with identifier"""
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code}"],
                "identifier": ["https://example.org|abc-123"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("cannot be used with", json.loads(response["body"])["issue"][0]["diagnostics"])
        self.service.search_immunizations.assert_not_called()

    def test_search_by_target_disease_returns_200_empty_bundle_when_all_codes_not_in_mapping(self):
        """it should return 200 with empty searchset when all target-disease codes are not in mapping"""
        self.mock_redis.hget.return_value = json.dumps(["840539006"])
        self.mock_redis.hgetall.return_value = {}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code}"],
            },
        }
        self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.return_value = Bundle.construct(
            entry=[],
            link=[BundleLink.construct(relation="self", url="url")],
            type="searchset",
            total=0,
        )

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 200)
        self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.assert_called_once()
        call_args = self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.call_args
        self.assertEqual(call_args[0][0], self.nhs_number_valid_value)
        self.assertEqual(
            call_args[0][4],
            {f"{self.snomed_system}|{self.measles_code}"},
        )
        self.assertEqual(call_args[1], {})
        self.service.search_immunizations.assert_not_called()

    def test_search_by_target_disease_returns_200_empty_bundle_when_target_disease_list_cache_missing(self):
        """it should return 200 with empty searchset when target-disease list is missing from cache"""
        self.mock_redis.hget.return_value = None
        self.mock_redis.hgetall.return_value = {}
        self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.return_value = Bundle.construct(
            entry=[],
            link=[BundleLink.construct(relation="self", url="url")],
            type="searchset",
            total=0,
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code}"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 200)
        self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.assert_called_once()
        call_args = self.service.make_empty_search_bundle_with_target_disease_not_in_mapping.call_args
        self.assertEqual(call_args[0][0], self.nhs_number_valid_value)
        self.assertEqual(
            call_args[0][4],
            {f"{self.snomed_system}|{self.measles_code}"},
        )
        self.service.search_immunizations.assert_not_called()

    def test_search_by_target_disease_with_date_range(self):
        """it should pass date params through to service when searching by target-disease"""
        self.mock_redis.hget.side_effect = self._hget_target_disease_codes_and_mmr
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[],
            link=[BundleLink.construct(relation="self", url="url")],
            type="searchset",
            total=0,
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code}"],
                "-date.from": ["2025-01-01"],
                "-date.to": ["2025-12-31"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 200)
        self.service.search_immunizations.assert_called_once_with(
            self.nhs_number_valid_value,
            {"MMR", "MMRV"},
            "test",
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
            None,
            None,
            {f"{self.snomed_system}|{self.measles_code}"},
            [],
        )

    def test_search_by_target_disease_returns_400_when_all_format_invalid(self):
        """it should return 400 when all target-disease values have invalid format"""
        self.mock_redis.hget.return_value = json.dumps([])
        self.mock_redis.hgetall.return_value = {}
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: ["no-pipe,wrong_system|123"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("target-disease", body["issue"][0]["diagnostics"])
        self.service.search_immunizations.assert_not_called()

    def test_search_by_target_disease_with_mixed_valid_and_invalid_returns_200_with_operation_outcome(self):
        """it should return 200 with results and OperationOutcome for invalid when one code valid and one invalid"""
        self.mock_redis.hget.side_effect = self._hget_target_disease_codes_and_mmr
        self.service.search_immunizations.return_value = Bundle.construct(
            entry=[BundleEntry.construct(resource=Immunization.construct(**{"id": "imms-1"}))],
            link=[BundleLink.construct(relation="self", url="search-url")],
            type="searchset",
            total=1,
        )
        lambda_event = {
            "headers": {"SupplierSystem": "test"},
            "multiValueQueryStringParameters": {
                self.patient_identifier_key: [self.patient_identifier_valid_value],
                self.target_disease_key: [f"{self.snomed_system}|{self.measles_code},invalid-no-pipe"],
            },
        }

        response = self.controller.search_immunizations(lambda_event)

        self.assertEqual(response["statusCode"], 200)
        self.service.search_immunizations.assert_called_once()
        call_args = self.service.search_immunizations.call_args
        self.assertEqual(call_args[0][0], self.nhs_number_valid_value)
        self.assertCountEqual(call_args[0][1], {"MMR", "MMRV"})
        self.assertEqual(call_args[1]["target_disease_codes_for_url"], {f"{self.snomed_system}|{self.measles_code}"})
        self.assertEqual(len(call_args[1]["invalid_target_diseases"]), 1)
        self.assertIn("invalid-no-pipe", call_args[1]["invalid_target_diseases"][0])
        self.assertIn("Invalid format", call_args[1]["invalid_target_diseases"][0])
