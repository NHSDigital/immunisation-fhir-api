"""Practitioner FHIR R4B validator"""
from fhir.resources.R4B.practitioner import Practitioner
from models.practitioner_pre_validators import PractitionerPreValidators


class PractitionerValidator:
    """
    Validate the practitioner record against the NHS specific validators and Practitioner
    FHIR profile
    """

    def __init__(self) -> None:
        pass

    @classmethod
    def pre_validate_name(cls, values: dict) -> dict:
        """Pre-validate that, if name exists, then it is an array of length 1"""
        try:
            name = values["name"]
            PractitionerPreValidators.name(name)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_name_given(cls, values: dict) -> dict:
        """
        Pre-validate that, if name[0] -> given (performing_professional_forename) exists,
        then it is an array contianing a single non-empty string
        """
        try:
            name_given = values["name"][0]["given"]
            PractitionerPreValidators.name_given(name_given)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_name_family(cls, values: dict) -> dict:
        """
        Pre-validate that, if name[0] -> family (performing_professional_surname) exists,
        then it is a non-empty string
        """

        try:
            name_family = values["name"][0]["family"]
            PractitionerPreValidators.name_family(name_family)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier exists, then it is a list of length 1
        """
        try:
            identifier = values["identifier"]
            PractitionerPreValidators.identifier(identifier)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0] -> value (performing_professional_body_reg_code) exists,
        then it is a non-empty string
        """
        try:
            identifier_value = values["identifier"][0]["value"]
            PractitionerPreValidators.identifier_value(identifier_value)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0] -> system (performing_professional_body_reg_uri) exists,
        then it is a non-empty string
        """
        try:
            identifier_system = values["identifier"][0]["system"]
            PractitionerPreValidators.identifier_system(identifier_system)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_type_coding(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0] -> type -> coding exists, then it is a list of length 1
        """
        try:
            identifier_type_coding = values["identifier"][0]["type"]["coding"]
            PractitionerPreValidators.identifier_type_coding(identifier_type_coding)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_type_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0] -> type -> coding -> display (sds_job_role_name) exists,
        then it is a non-empty string
        """
        try:
            identifier_type_coding_display = values["identifier"][0]["type"]["coding"][
                0
            ]["display"]
            PractitionerPreValidators.identifier_type_coding_display(
                identifier_type_coding_display
            )
        except KeyError:
            pass

        return values

    def add_custom_root_validators(self):
        """Add custom NHS validators to the model"""
        Practitioner.add_root_validator(self.pre_validate_name, pre=True)
        Practitioner.add_root_validator(self.pre_validate_name_given, pre=True)
        Practitioner.add_root_validator(self.pre_validate_name_family, pre=True)
        Practitioner.add_root_validator(self.pre_validate_identifier, pre=True)
        Practitioner.add_root_validator(self.pre_validate_identifier_value, pre=True)
        Practitioner.add_root_validator(self.pre_validate_identifier_system, pre=True)
        Practitioner.add_root_validator(
            self.pre_validate_identifier_type_coding, pre=True
        )
        Practitioner.add_root_validator(
            self.pre_validate_identifier_type_coding_display, pre=True
        )

    def validate(self, json_data) -> Practitioner:
        """Generate the Practitioner model from the JSON data"""
        return Practitioner.parse_obj(json_data)
