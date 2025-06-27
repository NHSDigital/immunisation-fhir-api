"FHIR Immunization Post Validators"

from models.errors import MandatoryError
from models.obtain_field_value import ObtainFieldValue
from models.validation_sets import ValidationSets
from models.mandation_functions import MandationFunctions
from models.field_names import FieldNames
from models.field_locations import FieldLocations
from base_utils.base_utils import obtain_field_value, obtain_field_location


class PostValidators:
    """FHIR Immunization Post Validators"""

    def __init__(self, imms, vaccine_type):
        self.imms = imms
        self.vaccine_type = vaccine_type
        self.errors = []

        # Note that the majority of fields require standard validation. Exception not included in the below list is
        # reason_code_coding_code, which has its own bespoke validation function.
        # Status is mandatory in FHIR, so there is no post-validation for status as it is handled by the FHIR validator.
        # NOTE: SOME FIELDS ARE COMMENTED OUT AS THEY ARE REQUIRED ELEMENTS (VALIDATION SHOULD ALWAYS PASS), AND THE
        # MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE FIELDS, THEY MAY NEED REINSTATED LATER.
        self.fields_with_standard_validation = [
            FieldNames.patient_identifier_value,
            FieldNames.patient_name_given,
            FieldNames.patient_name_family,
            FieldNames.patient_birth_date,
            FieldNames.patient_gender,
            FieldNames.patient_address_postal_code,
            FieldNames.occurrence_date_time,
            FieldNames.organization_identifier_value,
            FieldNames.organization_identifier_system,
            FieldNames.identifier_value,
            FieldNames.identifier_system,
            FieldNames.practitioner_name_given,
            FieldNames.practitioner_name_family,
            FieldNames.recorded,
            FieldNames.primary_source,
            FieldNames.vaccination_procedure_code,
            # FieldNames.vaccination_procedure_display,
            FieldNames.dose_number_positive_int,
            # FieldNames.vaccine_code_coding_code,
            # FieldNames.vaccine_code_coding_display,
            FieldNames.manufacturer_display,
            FieldNames.lot_number,
            FieldNames.expiration_date,
            # FieldNames.site_coding_code,
            # FieldNames.site_coding_display,
            # FieldNames.route_coding_code,
            # FieldNames.route_coding_display,
            FieldNames.dose_quantity_value,
            FieldNames.dose_quantity_code,
            FieldNames.dose_quantity_unit,
            FieldNames.location_identifier_value,
            FieldNames.location_identifier_system,
        ]

    def run_field_validation(
        self,
        mandation_functions: MandationFunctions,
        validation_set: dict,
        field_name: str,
        field_location: str,
        field_value: any,
    ) -> None:
        """Ascertains the correct mandation rule from the given validation set and applies the validation"""

        # Determine the mandation rule to be followed
        mandation_rule = validation_set[field_name]

        # Obtain the relevant mandation function to apply the mandation rule
        mandation_function = getattr(mandation_functions, mandation_rule)

        # Run the mandation function
        try:
            mandation_function(field_value=field_value, field_location=field_location)

        # Capture any validation errors in self.errors
        except MandatoryError as e:
            self.errors.append(str(e))

    def validate_field(
        self,
        mandation_functions: MandationFunctions,
        validation_set: dict,
        field_name: str,
        field_locations: FieldLocations,
    ) -> None:
        """Runs standard validation for the field"""

        field_location = obtain_field_location(field_name, field_locations)
        field_value = obtain_field_value(self.imms, field_name)
        self.run_field_validation(mandation_functions, validation_set, field_name, field_location, field_value)

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # def validate_reason_code_coding_code(self, mandation_functions: MandationFunctions, validation_set: dict):
    #     """
    #     Runs standard validation for each instance of reason_code_coding_code (note that, because reason_code
    #     is a list, there may be multiple instances of reason_code_coding_code, hence the need to iterate).
    #     """

    #     # Identify the number of elements of reason_code for validation to inform the number of times to iterate.
    #     # If there are no elements then set number of iterations to 1 as validation must be run at least once.
    #     number_of_iterations = len(self.imms["reasonCode"]) if self.imms.get("reasonCode") else 1

    #     # Validate the field for each element of reason_code
    #     for index in range(number_of_iterations):

    #         field_name = FieldNames.reason_code_coding_code
    #         field_location = f"reasonCode[{index}].coding[0].code"

    #         # Obtain the field value from the imms json data, or set it to None if the value can't be found
    #         try:
    #             field_value = getattr(ObtainFieldValue, field_name)(self.imms, index)
    #         except (KeyError, IndexError):
    #             field_value = None

    #         self.run_field_validation(mandation_functions, validation_set, field_name, field_location, field_value)

    def validate(self):
        """Run all post-validation checks."""

        # Initialise the mandation validation functions
        mandation_functions = MandationFunctions(self.imms, self.vaccine_type)

        # Obtain the relevant validation set
        validation_set = getattr(ValidationSets, self.vaccine_type.lower(), ValidationSets.vaccine_type_agnostic)

        # Create an instance of FieldLocations and set dynamic fields
        field_locations = FieldLocations()
        field_locations.set_dynamic_fields(self.imms)

        # Validate all fields which have standard validation
        for field_name in self.fields_with_standard_validation:
            self.validate_field(mandation_functions, validation_set, field_name, field_locations)

        # Validate reason_code_coding_code fields. Note that there may be multiple of each of these
        # - all instances of the field will be validated by the validate_reason_code_coding_field validator
        # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS), AND THE
        # MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
        # self.validate_reason_code_coding_code(mandation_functions, validation_set)

        # Raise any errors
        if self.errors:
            all_errors = "; ".join(self.errors)
            raise ValueError(f"Validation errors: {all_errors}")
