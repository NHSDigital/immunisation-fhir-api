"""Validation sets for each vaccine type"""

from models.mandation_functions import MandationRules
from mappings import VaccineTypes


class ValidationSets:
    """
    Validation sets for each vaccine type.
    Each validation set identifies the mandation rule which applies for each field.

    TO ADD A NEW VACCINE TYPE:
    * If the mandation rules for the new vaccine type are identical to the vaccine_type_agnostic rules, then
      add the vaccine type to the vaccine_types_which_use_agnostic_set list.
    * If some of the mandation rules for the new vaccine type are different than the agnostic rules, then create a
      new validation set, with the same name as the vaccine type. This can be done by copying and pasting the
      vaccine_type_agnostic set, and amending any rules as required.
    The validator will then automatically pick up the correct validation set.
    """

    def __init__(self) -> None:
        pass

    vaccine_types_which_use_agnostic_set = [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr,VaccineTypes.rsv]

    vaccine_type_agnostic = {
        "patient_identifier_value": MandationRules.required,
        "patient_name_given": MandationRules.mandatory,
        "patient_name_family": MandationRules.mandatory,
        "patient_birth_date": MandationRules.mandatory,
        "patient_gender": MandationRules.mandatory,
        "patient_address_postal_code": MandationRules.mandatory,
        "occurrence_date_time": MandationRules.mandatory,
        "organization_identifier_value": MandationRules.mandatory,
        "organization_identifier_system": MandationRules.mandatory,
        "identifier_value": MandationRules.mandatory,
        "identifier_system": MandationRules.mandatory,
        "practitioner_name_given": MandationRules.optional,
        "practitioner_name_family": MandationRules.optional,
        "recorded": MandationRules.mandatory,
        "primary_source": MandationRules.mandatory,
        "vaccination_procedure_code": MandationRules.mandatory,
        "vaccination_procedure_display": MandationRules.required,
        "dose_number_positive_int": MandationRules.required,
        "vaccine_code_coding_code": MandationRules.required,
        "vaccine_code_coding_display": MandationRules.required,
        "manufacturer_display": MandationRules.required,
        "lot_number": MandationRules.required,
        "expiration_date": MandationRules.required,
        "site_coding_code": MandationRules.required,
        "site_coding_display": MandationRules.required,
        "route_coding_code": MandationRules.required,
        "route_coding_display": MandationRules.required,
        "dose_quantity_value": MandationRules.required,
        "dose_quantity_code": MandationRules.required,
        "dose_quantity_unit": MandationRules.required,
        "reason_code_coding_code": MandationRules.required,
        "location_identifier_value": MandationRules.mandatory,
        "location_identifier_system": MandationRules.mandatory,
    }
