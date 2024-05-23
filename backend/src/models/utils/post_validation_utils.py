from typing import Literal, Optional, Any

from mappings import Mandation, vaccine_type_applicable_validations
from .generic_utils import (
    get_deep_attr,
    get_generic_questionnaire_response_value_from_model,
)


class MandatoryError(Exception):
    def __init__(self, message=None):
        self.message = message


class NotApplicableError(Exception):
    def __init__(self, message=None):
        self.message = message


class PostValidation:
    @staticmethod
    def check_mandation_requirements_met(
        field_value,
        field_location,
        mandation: str = None,
        vaccine_type: str = None,
        mandation_key: str = None,
        bespoke_mandatory_error_message: str = None,
        bespoke_not_applicable_error_message: str = None,
    ):
        """
        Check that the field_value meets the mandation requirements (if field_value can't be found
        then this argument should be given as None).

        If mandation is not yet known, pass the mandation_key and vaccine_type instead to allow a
        lookup.

        Generic mandatory and not-applicable error messages will be used if the appropriate optional
        arguments are not given.
        """

        # Determine and set the mandation and appropriate error messages
        mandation = mandation if mandation else vaccine_type_applicable_validations[mandation_key][vaccine_type]

        # Raise error messages where applicable
        if field_value is None and mandation == Mandation.mandatory:
            mandatory_error_message = (
                bespoke_mandatory_error_message
                if bespoke_mandatory_error_message
                else f"{field_location} is a mandatory field"
            )
            raise MandatoryError(mandatory_error_message)

        if field_value and mandation == Mandation.not_applicable:
            not_applicable_error_message = (
                bespoke_not_applicable_error_message
                if bespoke_not_applicable_error_message
                else f"{field_location} must not be provided for this vaccine type"
            )
            raise NotApplicableError(not_applicable_error_message)

    @staticmethod
    def get_generic_field_value(values, key, index=None, attribute=None):
        """
        Find the value of a field, using the key, index (if applicable) and attribute
        (if applicable) in the path to obtain it from values.

        NOTE: This function can only be used where the field path doesn't need to query the value
        of another field.
        """
        try:
            obj = getattr(values, key) if index is None else getattr(values, key)[index]
            field_value = obj if attribute is None else get_deep_attr(obj, attribute)
        except (KeyError, IndexError, AttributeError, TypeError):
            field_value = None

        return field_value

    @staticmethod
    def get_generic_questionnaire_response_value(
        values: dict,
        link_id: str,
        answer_type: Literal["valueBoolean", "valueString", "valueDateTime", "valueCoding"],
        field_type: Optional[Literal["code", "display", "system"]] = None,
    ) -> Any:
        try:
            field_value = get_generic_questionnaire_response_value_from_model(values, link_id, answer_type, field_type)
        except (KeyError, IndexError, AttributeError):
            field_value = None

        return field_value
