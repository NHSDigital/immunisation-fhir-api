"""Immunization FHIR R4B validator"""

from fhir.resources.R4B.immunization import Immunization
from models.fhir_immunization_pre_validators import PreValidators
from models.fhir_immunization_post_validators import PostValidators
from models.utils.validation_utils import get_vaccine_type


class ImmunizationValidator:
    """
    Validate the FHIR Immunization Resource JSON data against the NHS specific validators
    and Immunization FHIR profile
    """

    def __init__(self, add_post_validators: bool = True) -> None:
        self.add_post_validators = add_post_validators

    @staticmethod
    def run_pre_validators(immunization: dict) -> None:
        """Run pre validation on the FHIR Immunization Resource JSON data"""
        if error := PreValidators(immunization).validate():
            raise ValueError(error)

    @staticmethod
    def run_fhir_validators(immunization: dict) -> None:
        """Run the FHIR validator on the FHIR Immunization Resource JSON data"""
        Immunization.parse_obj(immunization)

    @staticmethod
    def run_post_validators(immunization: dict, vaccine_type: str) -> None:
        """Run post validation on the FHIR Immunization Resource JSON data"""
        if error := PostValidators(immunization, vaccine_type).validate():
            raise ValueError(error)

    # TODO: Update this function as reduce_validation_code is no longer found in the payload after data minimisation
    @staticmethod
    def is_reduce_validation():
        """Identify if reduced validation applies (default to false if no reduce validation information is given)"""
        return False

    def validate(self, immunization_json_data: dict) -> Immunization:
        """
        Generate the Immunization model. Note that run_pre_validators, run_fhir_validators, get_vaccine_type and
        run_post_validators will each raise errors if validation is failed.
        """
        # Identify whether to apply reduced validation
        reduce_validation = self.is_reduce_validation()

        # Pre-FHIR validations
        self.run_pre_validators(immunization_json_data)

        # FHIR validations
        self.run_fhir_validators(immunization_json_data)

        # Identify and validate vaccine type
        vaccine_type = get_vaccine_type(immunization_json_data)

        # Post-FHIR validations
        if self.add_post_validators and not reduce_validation:
            self.run_post_validators(immunization_json_data, vaccine_type)

    def run_postalCode_validator(self, values: dict) -> None:
        """Run pre validation on the FHIR Immunization Resource JSON data"""
        if error := PreValidators.pre_validate_patient_address_postal_code(
            self, values
        ):
            raise ValueError(error)
        else:
            pass
