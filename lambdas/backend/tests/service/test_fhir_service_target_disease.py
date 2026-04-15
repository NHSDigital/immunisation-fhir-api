import datetime
import unittest
from unittest.mock import create_autospec, patch

from authorisation.authoriser import Authoriser
from repository.fhir_repository import ImmunizationRepository
from service.fhir_service import FhirService


class TestSearchImmunizationsTargetDisease(unittest.TestCase):
    """Tests for FhirService search_immunizations and make_empty_search_bundle when using target-disease."""

    def setUp(self):
        super().setUp()
        self.authoriser = create_autospec(Authoriser)
        self.imms_repo = create_autospec(ImmunizationRepository)
        self.fhir_service = FhirService(self.imms_repo, self.authoriser)
        self.env_patcher = patch("service.fhir_service.IMMUNIZATION_ENV", "internal-dev")
        self.env_patcher.start()
        self.base_path_patcher = patch("service.fhir_service.IMMUNIZATION_BASE_PATH", "immunisation-fhir-api/FHIR/R4")
        self.base_path_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_make_empty_search_bundle_with_target_disease_not_in_mapping_returns_bundle_with_operation_outcome(self):
        """it should return searchset bundle with total 0 and one OperationOutcome warning"""
        result = self.fhir_service.make_empty_search_bundle_with_target_disease_not_in_mapping(
            nhs_number="9000000009",
            date_from=datetime.date(2025, 1, 1),
            date_to=None,
            include=None,
            target_disease_codes_for_url={"http://snomed.info/sct|14189004"},
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(result.total, 0)
        self.assertEqual(len(result.entry), 1)
        entry_resource = result.entry[0].resource
        res = entry_resource if isinstance(entry_resource, dict) else entry_resource.dict()
        self.assertEqual(res["resourceType"], "OperationOutcome")
        self.assertIn("target disease", res["issue"][0]["diagnostics"])
        self.assertEqual(len(result.link), 1)
        self.assertIn("target-disease=", result.link[0].url)
        self.assertIn("14189004", result.link[0].url)

    def test_search_immunizations_with_target_disease_codes_for_url_echoes_target_disease_in_bundle_link(self):
        """it should include target-disease param in bundle self link when target_disease_codes_for_url is set"""
        self.authoriser.filter_permitted_vacc_types.return_value = {"MMR"}
        self.imms_repo.find_immunizations.return_value = []

        result = self.fhir_service.search_immunizations(
            "9000000009",
            {"MMR"},
            "Test",
            None,
            None,
            None,
            invalid_immunization_targets=None,
            target_disease_codes_for_url={"http://snomed.info/sct|14189004"},
            invalid_target_diseases=None,
        )

        self.assertEqual(result.type, "searchset")
        self.assertEqual(len(result.link), 1)
        self.assertIn("target-disease=", result.link[0].url)
        self.assertIn("14189004", result.link[0].url)
        self.assertNotIn("-immunization.target", result.link[0].url)

    def test_search_immunizations_with_invalid_target_diseases_adds_operation_outcomes(self):
        """it should add one OperationOutcome entry per invalid target disease diagnostic"""
        self.authoriser.filter_permitted_vacc_types.return_value = {"MMR"}
        self.imms_repo.find_immunizations.return_value = []

        result = self.fhir_service.search_immunizations(
            "9000000009",
            {"MMR"},
            "Test",
            None,
            None,
            None,
            invalid_immunization_targets=None,
            target_disease_codes_for_url={"http://snomed.info/sct|14189004"},
            invalid_target_diseases=[
                "Target disease code '99999' is not a supported target disease in this service.",
            ],
        )

        outcomes = [
            e
            for e in result.entry
            if (e.resource if isinstance(e.resource, dict) else e.resource.dict()).get("resourceType")
            == "OperationOutcome"
        ]
        self.assertEqual(len(outcomes), 1)
        oo_dict = outcomes[0].resource if isinstance(outcomes[0].resource, dict) else outcomes[0].resource.dict()
        self.assertIn("99999", oo_dict["issue"][0]["diagnostics"])
