"""Tests for convert_to_fhir_imms_resource"""
import unittest
from typing import Tuple, List
from unittest.mock import patch

from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFhirImmsResources,
    MockFieldDictionaries,
    TargetDiseaseElements
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from convert_to_fhir_imms_resource import (
        _decorate_immunization,
        _get_decorators_for_action_flag,
        all_decorators,
        convert_to_fhir_imms_resource,
        ImmunizationDecorator
    )


class TestConvertToFhirImmsResource(unittest.TestCase):
    """Tests for convert_to_fhir_imms_resource"""

    def test_convert_to_fhir_imms_resource(self):
        """
        Test that convert_to_fhir_imms_resource gives the expected output. These tests check that the entire
        outputted FHIR Immunization Resource matches the expected output.
        """

        # Test cases tuples are structured as (test_name, input_values, expected_output, action_flag)
        test_cases = [
            ("All fields", MockFieldDictionaries.all_fields, MockFhirImmsResources.all_fields, "UPDATE"),
            (
                "Mandatory fields only",
                MockFieldDictionaries.mandatory_fields_only,
                MockFhirImmsResources.mandatory_fields_only,
                "UPDATE"
            ),
            (
                "Critical fields only",
                MockFieldDictionaries.critical_fields_only,
                MockFhirImmsResources.critical_fields,
                "NEW"
            ),
            (
                "Delete action only converts minimal fields",
                MockFieldDictionaries.mandatory_fields_delete_action,
                MockFhirImmsResources.delete_operation_fields,
                "DELETE"
            )
        ]

        for test_name, input_values, expected_output, action_flag in test_cases:
            with self.subTest(test_name):
                output = convert_to_fhir_imms_resource(input_values, TargetDiseaseElements.RSV, action_flag)
                self.assertEqual(output, expected_output)

    def test_get_decorators_for_action_flag(self):
        """
        Test that the _test_get_decorators_for_action_flag function returns the correct list of decorators based on the
        action flag provided.
        """
        test_cases: List[Tuple[str, str, List[ImmunizationDecorator]]] = [
            ("Delete action only returns one decorator", "DELETE", [_decorate_immunization]),
            ("Update action returns all decorators", "UPDATE", all_decorators),
            ("Create action returns all decorators", "CREATE", all_decorators)
        ]

        for test_name, action_flag, expected_decorators in test_cases:
            with self.subTest(test_name):
                result = _get_decorators_for_action_flag(action_flag)
                self.assertEqual(result, expected_decorators)
