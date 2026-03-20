"""Tests for the search_url_helper file"""

import datetime
import unittest

from service.search_url_helper import create_url_for_bundle_link


class TestServiceUrl(unittest.TestCase):
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
