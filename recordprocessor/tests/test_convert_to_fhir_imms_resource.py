"""Tests for convert_to_fhir_imms_resource"""
import json
import unittest
from unittest.mock import patch

from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFhirImmsResources,
    MockFieldDictionaries,
    TargetDiseaseElements
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from convert_to_fhir_imms_resource import convert_to_fhir_imms_resource


class TestConvertToFhirImmsResource(unittest.TestCase):
    """Tests for convert_to_fhir_imms_resource"""

    def test_convert_to_fhir_imms_resource(self):
        """
        Test that convert_to_fhir_imms_resource gives the expected output. These tests check that the entire
        outputted FHIR Immunization Resource matches the expected output.
        """

        # Test cases tuples are structure as (test_name, input_values, expected_output)
        cases = [
            ("All fields", MockFieldDictionaries.all_fields, MockFhirImmsResources.all_fields),
            (
                "Mandatory fields only",
                MockFieldDictionaries.mandatory_fields_only,
                MockFhirImmsResources.mandatory_fields_only,
            ),
            (
                "Critical fields only",
                MockFieldDictionaries.critical_fields_only,
                MockFhirImmsResources.critical_fields,
            ),
        ]

        for test_name, input_values, expected_output in cases:
            with self.subTest(test_name):
                output = convert_to_fhir_imms_resource(input_values, TargetDiseaseElements.RSV)
                self.assertEqual(output, expected_output)
