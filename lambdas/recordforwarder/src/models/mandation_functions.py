"""Functions for validating that mandation requirements are met"""

from dataclasses import dataclass

from models.errors import MandatoryError


@dataclass
class MandationRules:
    """Class containing all the mandation rules, which have corresponding mandation functions"""

    mandatory = "mandatory"
    required = "required"
    optional = "optional"


class MandationFunctions:
    """
    Class containing functions for validating that mandation rules are met.
    Each instance of the class must be initialised with the FHIR Immunization resource JSON data, and the vaccine type.
    Each mandation function takes the field_value and field_location as arguments and raises an error if the field_value
    does not comply with the mandation rule.
    """

    def __init__(self, imms: dict, vaccine_type: str) -> None:
        self.imms = imms
        self.vaccine_type = vaccine_type

    def mandatory(self, field_value, field_location: str) -> None:
        """Raises MandatoryError if field value is None"""
        if field_value is None:
            raise MandatoryError(f"{field_location} is a mandatory field")

    def required(self, field_value, field_location: str) -> None:
        """Allows all field values to pass"""

    def optional(self, field_value, field_location: str) -> None:
        """Allows all field values to pass"""
