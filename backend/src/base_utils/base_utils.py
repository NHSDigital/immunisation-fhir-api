"""Utils for backend src code"""

from models.obtain_field_value import ObtainFieldValue
from models.field_locations import FieldLocations


def obtain_field_value(imms: dict, field_name: str) -> any:
    """Finds and returns the field value from the imms json data. Returns none if field not found."""

    # Obtain the function for extracting the field value from the json data
    function_for_obtaining_field_value = getattr(ObtainFieldValue, field_name)

    # Obtain the field value, or set it to none if it can't be found
    try:
        field_value = function_for_obtaining_field_value(imms)
    except (KeyError, IndexError, TypeError):
        field_value = None

    return field_value


def obtain_field_location(
    field_name: str, field_locations: FieldLocations = FieldLocations()
) -> str:
    """
    Obtains the field location of the given field from an instance of the FieldLocations class.
    NOTE: Some field locations need to be dynamically set. If this is required then
    these fields should be set on an instance of FieldLocations, and the instance passed to this funciton as an arg.
    """
    return getattr(field_locations, field_name)
