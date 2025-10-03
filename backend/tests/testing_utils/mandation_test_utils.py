"""Mandation test utilities"""

import unittest
from copy import deepcopy
from pydantic import ValidationError

from jsonpath_ng.ext import parse


class MandationTests:
    """Test for presence of fields with different mandation levels"""

    @staticmethod
    def prepare_json_data(test_instance: unittest.TestCase, json_data: dict = None) -> dict:
        """Returns json_data if given json_data, otherwise returns the complete covid19 json data as a default"""
        return json_data if json_data else test_instance.completed_json_data["COVID19"]

    @staticmethod
    def test_present_field_accepted(test_instance: unittest.TestCase, valid_json_data: dict = None):
        """Test that JSON data is accepted when a field is present"""
        valid_json_data = MandationTests.prepare_json_data(test_instance, valid_json_data)
        test_instance.assertIsNone(test_instance.validator.validate(valid_json_data))

    @staticmethod
    def test_missing_field_accepted(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_json_data: dict = None,
    ):
        """Test that JSON data which is missing a required,optional or not applicable field is accepted"""
        # Prepare the data
        valid_json_data = MandationTests.prepare_json_data(test_instance, valid_json_data)
        valid_json_data = parse(field_location).filter(lambda d: True, valid_json_data)

        # Test that the valid data is accepted by the model
        test_instance.assertIsNone(test_instance.validator.validate(valid_json_data))

    @staticmethod
    def test_missing_mandatory_field_rejected(
        test_instance: unittest.TestCase,
        field_location: str,
        valid_json_data: dict = None,
        expected_error_message: str = None,
        expected_error_type: str = "value_error",
        is_mandatory_fhir: bool = False,
    ):
        """
        Test that json data which is missing a mandatory field is rejected by the model, with
        an appropriate validation error. Note that missing mandatory FHIR fields are rejected
        by the FHIR validator, whereas missing mandatory NHS fields are rejected by the custom
        validator.

        NOTE:
        TypeErrors and ValueErrors are caught and converted to ValidationErrors by pydantic. When
        this happens, the error message is suffixed with the type of error e.g. type_error or
        value_error. This is why the test checks for the type of error in the error message.
        """
        # Prepare the json data
        valid_json_data = MandationTests.prepare_json_data(test_instance, valid_json_data)
        invalid_json_data = parse(field_location).filter(lambda d: True, valid_json_data)

        # Set the expected error message
        expected_error_message = (
            expected_error_message if expected_error_message else f"Validation errors: {field_location} is a mandatory field"
        )

        if is_mandatory_fhir:
            # Test that correct error message is raised
            with test_instance.assertRaises(ValidationError) as error:
                test_instance.validator.validate(invalid_json_data)
            test_instance.assertTrue(
                (expected_error_message + f" (type={expected_error_type})") in str(error.exception)
            )

        else:
            # Test that correct error message is raised
            with test_instance.assertRaises(ValueError) as error:
                test_instance.validator.validate(invalid_json_data)
            test_instance.assertEqual(expected_error_message, str(error.exception))
