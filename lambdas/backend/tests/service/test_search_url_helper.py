"""Tests for the search_url_helper file"""

import datetime
import unittest

from service.search_url_helper import create_url_for_bundle_link, get_service_url


class TestServiceUrl(unittest.TestCase):
    def test_get_service_url(self):
        """it should create service url"""
        test_cases = [
            ("pr-123", "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
            (None, "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
            ("preprod", "https://int.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
            ("prod", "https://api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
            ("ref", "https://ref.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
            ("internal-dev", "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
            ("internal-qa", "https://internal-qa.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"),
        ]
        mock_base_path = "immunisation-fhir-api/FHIR/R4"

        for mock_env, expected in test_cases:
            with self.subTest(mock_env=mock_env, expected=expected):
                self.assertEqual(get_service_url(mock_env, mock_base_path), expected)

    def test_get_service_url_uses_default_path_when_not_provided(self):
        self.assertEqual(
            get_service_url(None, None), "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4"
        )

    def test_create_url_for_bundle_link_with_target_disease_uses_target_disease_param(self):
        url = create_url_for_bundle_link(
            immunization_targets=set(),
            patient_nhs_number="9000000009",
            date_from=datetime.date(2025, 1, 1),
            date_to=None,
            include=None,
            service_env=None,
            service_base_path="immunisation-fhir-api/FHIR/R4",
            target_disease_codes_for_url={"http://snomed.info/sct|14189004", "http://snomed.info/sct|36989005"},
        )
        self.assertIn("target-disease=", url)
        self.assertIn("14189004", url)
        self.assertIn("36989005", url)
        self.assertIn("patient.identifier=", url)
        self.assertNotIn("immunization.target", url)

    def test_create_url_for_bundle_link_without_target_disease_uses_immunization_target(self):
        url = create_url_for_bundle_link(
            immunization_targets={"MMR", "COVID"},
            patient_nhs_number="9000000009",
            date_from=None,
            date_to=None,
            include=None,
            service_env=None,
            service_base_path="immunisation-fhir-api/FHIR/R4",
            target_disease_codes_for_url=None,
        )
        self.assertIn("-immunization.target=", url)
        self.assertIn("MMR", url)
        self.assertIn("COVID", url)
