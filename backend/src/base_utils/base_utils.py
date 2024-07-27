"""Utils for backend src code"""

from models.obtain_field_value import ObtainFieldValue
from models.field_locations import FieldLocations


def obtain_field_value(imms, field_name):
    """Finds and returns the field value from the imms json data. Returns none if field not found."""

    # Obtain the function for extracting the field value from the json data
    function_for_obtaining_field_value = getattr(ObtainFieldValue, field_name)

    # Obtain the field value, or set it to none if it can't be found
    try:
        field_value = function_for_obtaining_field_value(imms)
    except (KeyError, IndexError, TypeError):
        field_value = None

    return field_value


def obtain_field_location(field_name):
    """Returns the field location string"""
    return getattr(FieldLocations, field_name)
