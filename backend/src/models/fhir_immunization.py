"""Immunization FHIR R4B validator"""
import json
from typing import Literal

from fhir.resources.R4B.immunization import Immunization
from models.fhir_immunization_pre_validators import PreValidators
from models.fhir_immunization_post_validators import PostValidators
from models.utils.generic_utils import get_generic_questionnaire_response_value, get_generic_extension_value_from_model
from mappings import vaccination_procedure_snomed_codes
from models.utils.generic_utils import get_generic_questionnaire_response_value


class ImmunizationValidator:
    """
    Validate the FHIR Immunization model against the NHS specific validators and Immunization
    FHIR profile
    """

    def __init__(self, add_post_validators: bool = True, immunization: Immunization = None) -> None:
        self.immunization = immunization
        self.reduce_validation_code = False
        self.add_post_validators = add_post_validators
        self.pre_validators = None
        self.post_validators = None
        self.errors = []
        
    def initialize_immunization(self, json_data):
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
        """Set the reduce validation code"""
        reduce_validation_code = False

        # If reduce_validation_code field exists then retrieve it's value
        try:
            reduce_validation_code = get_generic_questionnaire_response_value(
                json_data, "ReduceValidation", "valueBoolean"
            )
        except (KeyError, IndexError, AttributeError, TypeError):
            pass
        finally:
            # If no value is given, then ReduceValidation default value is False
            if reduce_validation_code is None:
                reduce_validation_code = False

        self.reduce_validation_code = reduce_validation_code

    def set_vaccine_type(self, immunization):
        """Set vaccine type"""
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
        system = "http://snomed.info/sct"
        field_type = "code"
        try:
            vaccination_procedure_code = get_generic_extension_value_from_model(immunization, url, system, field_type)
            self.vaccine_type = vaccination_procedure_snomed_codes.get(
                vaccination_procedure_code, None
            )
        except (KeyError, IndexError, AttributeError, TypeError) as error:
            raise error

    def validate(self, json_data) -> Immunization:
        """Generate the Immunization model"""
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        self.set_reduce_validation_code(json_data)
        self.initialize_pre_validators(json_data)

        try:
            self.run_pre_validators()
        except Exception as e:
            raise e

        self.initialize_immunization(json_data)
        self.set_vaccine_type(self.immunization)

        if self.add_post_validators and not self.reduce_validation_code:
            self.initialize_post_validators(self.immunization)
            try:
                self.run_post_validators()
            except Exception as e:
                raise e

        return self.immunization
