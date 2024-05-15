"""Immunization FHIR R4B validator"""

from fhir.resources.R4B.immunization import Immunization
from models.fhir_immunization_pre_validators import PreValidators
from models.fhir_immunization_post_validators import PostValidators
from models.utils.generic_utils import get_generic_questionnaire_response_value


class ImmunizationValidator:
    """Validate the FHIR Immunization model against the NHS specific validators and Immunization FHIR profile"""

    def __init__(self, add_post_validators: bool = True) -> None:
        self.immunization: Immunization
        self.reduce_validation_code: bool
        self.add_post_validators = add_post_validators
        self.pre_validators: PreValidators
        self.post_validators: PostValidators
        self.errors = []

    def initialize_immunization_and_run_fhir_validators(self, json_data):
        """Initialize immunization with data after parsing it through the FHIR validator"""
        self.immunization = Immunization.parse_obj(json_data)

    def initialize_pre_validators(self, immunization):
        """Initialize pre validators with data."""
        self.pre_validators = PreValidators(immunization)

    def initialize_post_validators(self, immunization):
        """Initialize post validators with data"""
        self.post_validators = PostValidators(immunization)

    def run_pre_validators(self):
        """Run custom pre validators to the data"""
        error = self.pre_validators.validate()
        if error:
            raise ValueError(error)

    def run_post_validators(self):
        """Run custom pre validators to the data"""
        error = self.post_validators.validate()
        if error:
            raise ValueError(error)

    def set_reduce_validation_code(self, json_data):
        """Set the reduce validation code (default to false if no reduceValidation code is given)"""
        reduce_validation_code = False

        # If reduce_validation_code field exists then retrieve it's value
        try:
            reduce_validation_code = get_generic_questionnaire_response_value(
                json_data, "ReduceValidation", "valueBoolean"
            )
        except (KeyError, IndexError, AttributeError, TypeError):
            pass
        finally:
            if reduce_validation_code is None:
                reduce_validation_code = False

        self.reduce_validation_code = reduce_validation_code

    def validate(self, json_data) -> Immunization:
        """Generate the Immunization model"""
        self.set_reduce_validation_code(json_data)

        # Pre-FHIR validations
        self.initialize_pre_validators(json_data)
        try:
            self.run_pre_validators()
        except Exception as e:
            raise e

        # FHIR validations
        self.initialize_immunization_and_run_fhir_validators(json_data)

        # Post-FHIR validations
        if self.add_post_validators and not self.reduce_validation_code:
            self.initialize_post_validators(self.immunization)
            try:
                self.run_post_validators()
            except Exception as e:
                raise e

        return self.immunization