"""Generic utilities for models"""

import re
from datetime import datetime
from typing import Literal, Union


def generic_string_validation(
    field_value: str,
    field_location: str,
    defined_length: int = None,
    max_length: int = None,
    predefined_values: tuple = None,
):
    """
    Apply generic validation to a string field to ensure it is a non-empty string which meets
    the length requirements and predefined values requirements
    """
    if not isinstance(field_value, str):
        raise TypeError(f"{field_location} must be a string")

    if defined_length:
        if len(field_value) != defined_length:
            raise ValueError(f"{field_location} must be {defined_length} characters")
    else:
        if len(field_value) == 0:
            raise ValueError(f"{field_location} must be a non-empty string")

    if max_length:
        if len(field_value) > max_length:
            raise ValueError(
                f"{field_location} must be {max_length} or fewer characters"
            )

    if predefined_values:
        if field_value not in predefined_values:
            raise ValueError(
                f"{field_location} must be one of the following: "
                + str(", ".join(predefined_values))
            )


def generic_list_validation(
    field_value: list, field_location: str, defined_length: int = None
):
    """
    Apply generic validation to a list field to ensure it is a non-empty list which meets
    the length requirements
    """
    if not isinstance(field_value, list):
        raise TypeError(f"{field_location} must be an array")

    if defined_length:
        if len(field_value) != defined_length:
            raise ValueError(
                f"{field_location} must be an array of length {defined_length}"
            )
    else:
        if len(field_value) == 0:
            raise ValueError(f"{field_location} must be a non-empty array")


def generic_date_validation(field_value: str, field_location: str):
    """
    Apply generic validation to a date field to ensure that it is a string (JSON dates must be
    written as strings) containing a valid date in the format "YYYY-MM-DD"
    """
    if not isinstance(field_value, str):
        raise TypeError(f"{field_location} must be a string")

    try:
        datetime.strptime(field_value, "%Y-%m-%d").date()
    except ValueError as value_error:
        raise ValueError(
            f"{field_location} must be a valid date string in the format "
            + '"YYYY-MM-DD"'
        ) from value_error


def generic_date_time_validation(field_value: str, field_location: str):
    """
    Apply generic validation to a datetime field to ensure that it is a string (JSON dates must be
    written as strings) containing a valid datetime in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or
    "YYYY-MM-DDThh:mm:ss-zz:zz" (i.e. date and time, including timezone offset in hours and minutes)
    """

    if not isinstance(field_value, str):
        raise TypeError(f"{field_location} must be a string")

    date_time_pattern_with_timezone = re.compile(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\+|-)\d{2}:\d{2}"
    )

    if not date_time_pattern_with_timezone.fullmatch(field_value):
        raise ValueError(
            f'{field_location} must be a string in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or'
            + '"YYYY-MM-DDThh:mm:ss-zz:zz" (i.e date and time, including timezone offset in '
            + "hours and minutes)"
        )

    try:
        datetime.strptime(field_value, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError as value_error:
        raise ValueError(f"{field_location} must be a valid datetime") from value_error


def generic_boolean_validation(field_value: str, field_location: str):
    """Apply generic validation to a boolean field to ensure that it is a boolean"""
    if not isinstance(field_value, bool):
        raise TypeError(f"{field_location} must be a boolean")


def generic_positive_integer_validation(field_value: int, field_location: str):
    """Apply generic validation to an integer field to ensure that it is an integer"""
    if not isinstance(field_value, int):
        raise TypeError(f"{field_location} must be a positive integer")
    # Note that booleans are a sub-class of integers in python
    if isinstance(field_value, bool):
        raise TypeError(f"{field_location} must be a positive integer")
    if field_value <= 0:
        raise ValueError(f"{field_location} must be a positive integer")


def get_generic_questionnaire_response_value(
    json_data: dict, link_id: str, field_type: Literal["code", "display", "system"]
) -> Union[str, None]:
    """
    Get the value of a QuestionnaireResponse field, given its linkId
    """

    for record in json_data["contained"]:
        if record["resourceType"] == "QuestionnaireResponse":
            for item in record["item"]:
                if item["linkId"] == link_id:
                    return item["answer"][0]["valueCoding"][field_type]

    raise KeyError(
        "contained[0] -> resourceType[QuestionnaireResponse]: "
        + f"item[*] -> linkId[{link_id}]: answer[0] -> valueCoding -> {field_type} does not exist"
    )


def get_generic_extension_value(
    json_data: dict, url: str, field_type: Literal["code", "display", "system"]
) -> Union[str, None]:
    """
    Get the value of an extension field, given its url
    """

    for record in json_data["extension"]:
        if record["url"] == url:
            return record["valueCodeableConcept"]["coding"][0][field_type]

    raise KeyError(
        f"extension[*] -> url[{url}]: "
        + f"valueCodableConcept -> coding[0] -> {field_type} does not exist"
    )
