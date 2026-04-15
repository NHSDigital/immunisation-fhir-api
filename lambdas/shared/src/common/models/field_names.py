"""File containing name strings for each field of note"""

from dataclasses import dataclass


@dataclass
class FieldNames:
    """Stores the field name strings for fields of note within the FHIR Immunization Resource JSON data"""

    # Note: some field names are commented out as they are required elements (validation should always pass), and the
    # means to access the value has not been confirmed. Do not delete the field names, they may need reinstating later.

    # These are the field names that we may require to reinstate in the future:
    #   vaccination_procedure_display
    #   vaccine_code_coding_code
    #   vaccine_code_coding_display
    #   site_coding_code
    #   site_coding_display
    #   route_coding_code
    #   route_coding_display
    #   reason_code_coding_code

    target_disease = "target_disease"
    target_disease_codes = "target_disease_codes"
    patient_identifier_value = "patient_identifier_value"
    patient_name_given = "patient_name_given"
    patient_name_family = "patient_name_family"
    patient_birth_date = "patient_birth_date"
    patient_gender = "patient_gender"
    patient_address_postal_code = "patient_address_postal_code"
    occurrence_date_time = "occurrence_date_time"
    organization_identifier_value = "organization_identifier_value"
    organization_identifier_system = "organization_identifier_system"
    identifier_value = "identifier_value"
    identifier_system = "identifier_system"
    practitioner_name_given = "practitioner_name_given"
    practitioner_name_family = "practitioner_name_family"
    recorded = "recorded"
    primary_source = "primary_source"
    vaccination_procedure_code = "vaccination_procedure_code"
    dose_number_positive_int = "dose_number_positive_int"
    manufacturer_display = "manufacturer_display"
    lot_number = "lot_number"
    expiration_date = "expiration_date"
    dose_quantity_value = "dose_quantity_value"
    dose_quantity_code = "dose_quantity_code"
    dose_quantity_unit = "dose_quantity_unit"
    location_identifier_value = "location_identifier_value"
    location_identifier_system = "location_identifier_system"
