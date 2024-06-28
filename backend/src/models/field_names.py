"""
File containing the field location strings for identifying the location of a field within the FHIR immunization 
resource json data
"""

from dataclasses import dataclass


@dataclass
class FieldNames:
    """
    Stores the field location names for fields of note within the FHIR Immunization Resource JSON data
    """

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
    vaccination_procedure_display = "vaccination_procedure_display"
    dose_number_positive_int = "dose_number_positive_int"
    vaccine_code_coding_code = "vaccine_code_coding_code"
    vaccine_code_coding_display = "vaccine_code_coding_display"
    manufacturer_display = "manufacturer_display"
    lot_number = "lot_number"
    expiration_date = "expiration_date"
    site_coding_code = "site_coding_code"
    site_coding_display = "site_coding_display"
    route_coding_code = "route_coding_code"
    route_coding_display = "route_coding_display"
    dose_quantity_value = "dose_quantity_value"
    dose_quantity_code = "dose_quantity_code"
    dose_quantity_unit = "dose_quantity_unit"
    reason_code_coding_code = "reason_code_coding_code"
    location_identifier_value = "location_identifier_value"
    location_identifier_system = "location_identifier_system"
