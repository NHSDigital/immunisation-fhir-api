"""Immunization FHIR R4B validator"""

from fhir.resources.R4B.immunization import Immunization
from models.fhir_immunization_pre_validators import PreValidators
from models.fhir_immunization_post_validators import PostValidators
from models.utils.generic_utils import get_generic_questionnaire_response_value,extract_value
from models.schema import ImmunizationSchema
import json


class ImmunizationValidator:
    """Validate the FHIR Immunization model against the NHS specific validators and Immunization FHIR profile"""

    def __init__(self, add_post_validators: bool = True) -> None:
        self.immunization: Immunization
        self.reduce_validation_code: bool
        self.add_post_validators = add_post_validators
        self.pre_validators: PreValidators
        self.post_validators: PostValidators
        self.immunization_schema: ImmunizationSchema
        self.errors = []

    def initialize_immunization_and_run_fhir_validators(self, json_data):
        """Initialize immunization with data after parsing it through the FHIR validator"""
        print("4")
        try:
            self.immunization = Immunization.parse_obj(json_data)
        except Exception as e:
            raise ValueError(e)
    def initialize_pre_validators(self, immunization):
        """Initialize pre validators with data."""
        self.immunization_schema= ImmunizationSchema(context={'contained': immunization['contained']})
        print("5")
        errors = self.immunization_schema.validate(immunization)
        print(errors)
        if errors:
            error_list = []
            for key, value in errors.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            error_list.append({key: {sub_key: sub_value}})
                    else:
                        error_list.append({key: value})

                # Convert each dictionary in the list to a JSON-formatted string
            error_strings = [json.dumps(error) for error in error_list]

                # Extract content within the first and last square brackets and update the array
            updated_errors = [extract_value(item) for item in error_strings]
                # for error_string in error_strings:
                #     match = re.search(r'\[(.*?)\]', error_string)
                #     if match:
                #         updated_errors.append(match.group(1))
            error_string = '; '.join(updated_errors)
            raise ValueError(error_string)
        

    def initialize_post_validators(self, immunization):
        """Initialize post validators with data"""
        self.post_validators = PostValidators(immunization)

    # def run_pre_validators(self):
    #     """Run custom pre validators to the data"""
    #     error = self.pre_validators.validate()
    #     if error:
    #         raise ValueError(error)

    def run_post_validators(self):
        """Run custom post validators to the data"""
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
        # self.set_reduce_validation_code(json_data)
        
        print("3")
        # FHIR validations
        self.initialize_immunization_and_run_fhir_validators(json_data)
        
        # Pre-FHIR validations
        self.initialize_pre_validators(json_data)
        
        # Post-FHIR validations
        # if self.add_post_validators and not self.reduce_validation_code:
        #     self.initialize_post_validators(self.immunization)
        #     try:
        #         self.run_post_validators()
        #     except Exception as e:
        #         raise e

        return self.immunization
