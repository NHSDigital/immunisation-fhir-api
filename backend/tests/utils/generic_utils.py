"""Generic utils for tests"""

import json
import os
import unittest
from decimal import Decimal
from typing import Literal, Any
from jsonpath_ng.ext import parse


def load_json_data(filename: str):
    """Load the json data"""
    data_path = f"{os.path.dirname(os.path.abspath(__file__))}/../sample_data"
    immunization_file_path = f"{data_path}/{filename}"
    with open(immunization_file_path, "r", encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


def generate_field_location_for_questionnaire_response(
    link_id: str, field_type: Literal["code", "display", "system"]
) -> str:
    """Generate the field location string for questionnaire response items"""
    return (
        "contained[?(@.resourceType=='QuestionnaireResponse')]"
        + f".item[?(@.linkId=='{link_id}')].answer[0].valueCoding.{field_type}"
    )


def generate_field_location_for_extension(url: str, system: str, field_type: Literal["code", "display"]) -> str:
    """Generate the field location string for extension items"""
    return f"extension[?(@.url=='{url}')].valueCodeableConcept." + f"coding[?(@.system=='{system}')].{field_type}"


def update_target_disease_code(imms: dict, target_disease_code: str):
    """
    Update the disease code found at the first index of coding field,
    within the first index of targetDisease field with a new code
    """
    imms["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"] = target_disease_code


def test_valid_values_accepted(
    test_instance: unittest.TestCase,
    valid_json_data: dict,
    field_location: str,
    valid_values_to_test: list,
):
    """Test that valid json data is accepted by the model"""
    for valid_item in valid_values_to_test:
        # Update the value at the relevant field location to the valid value to be tested
        valid_json_data = parse(field_location).update(valid_json_data, valid_item)
        # Test that the valid data is accepted by the model
        test_instance.assertTrue(test_instance.validator.validate(valid_json_data))


def test_invalid_values_rejected(
    test_instance: unittest.TestCase,
    valid_json_data: dict,
    field_location: str,
    invalid_value: Any,
    expected_error_message: str,
):
    """
    Test that invalid json data is rejected by the model, with an appropriate validation error

    NOTE:
    TypeErrors and ValueErrors are caught and converted to ValidationErrors by pydantic. When
    this happens, the error message is suffixed with the type of error e.g. type_error or
    value_error. This is why the test checks for the type of error in the error message.
    """
    # Create invalid json data by amending the value of the relevant field
    invalid_json_data = parse(field_location).update(valid_json_data, invalid_value)

    # Test that correct error type is raised
    with test_instance.assertRaises(ValueError or TypeError) as error:
        test_instance.validator.validate(invalid_json_data)

    full_error_message = str(error.exception)

    actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
    test_instance.assertIn(expected_error_message, actual_error_messages)