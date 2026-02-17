"""Tests for the search_url_helper file"""

import unittest

from common.get_service_url import get_service_url


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
