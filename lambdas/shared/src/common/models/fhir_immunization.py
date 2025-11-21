"""Immunization FHIR R4B validator"""

from fhir.resources.R4B.immunization import Immunization

from common.models.constants import VALIDATION_SCHEMA_HASH_KEY
from common.models.errors import ValidatorError
from common.redis_client import get_redis_client
from common.validator.constants.enums import DataType
from common.validator.validator import Validator


class ImmunizationValidator:
    """
    Validate the FHIR Immunization Resource JSON data against the NHS specific validators
    and Immunization FHIR profile
    """

    @staticmethod
    def run_validator(immunization: dict, data_type: DataType = DataType.FHIR) -> None:
        """Run generic validation on the FHIR Immunization Resource data"""

        # TODO: raise an error if there is no schema file
        schema_file = get_redis_client().hget(VALIDATION_SCHEMA_HASH_KEY, "schema_file")
        validator = Validator(schema_file)
        if data_type == DataType.FHIR:
            errors = validator.validate_fhir(immunization)
        else:
            errors = validator.validate_csvrow(immunization)
        if errors:
            """
            errors_list = []
            for error_report in errors:
                errors_list.append(error_report.to_dict())
            errors_json = json.dumps(errors_list)
            print(f"\nValidator errors: {errors_json}")
            """
            raise ValidatorError(errors)

    @staticmethod
    def run_fhir_validators(immunization: dict) -> None:
        """Run the FHIR validator on the FHIR Immunization Resource JSON data"""
        Immunization.parse_obj(immunization)

    def validate(self, immunization_json_data: dict, data_type: DataType = DataType.FHIR) -> Immunization:
        """
        Generate the Immunization model. Note that run_validator and run_post_validators will each raise
        errors if validation is failed.
        """
        # Generic validator
        self.run_validator(immunization_json_data, data_type)

        # FHIR validations
        self.run_fhir_validators(immunization_json_data)
