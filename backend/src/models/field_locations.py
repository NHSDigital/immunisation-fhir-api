"""
File containing the field location strings for identifying the location of a field within the FHIR immunization
resource json data
"""

from dataclasses import dataclass, field

from models.utils.generic_utils import (
    generate_field_location_for_extension,
    patient_name_given_field_location,
    patient_name_family_field_location,
    practitioner_name_given_field_location,
    practitioner_name_family_field_location,
)

from constants import Urls


@dataclass
class FieldLocations:
    """
    Stores the field location strings for identifying the location of a field within the FHIR immunization resource
    json data
    """

    target_disease = "protocolApplied[0].targetDisease"
    target_disease_codes = (
        f"protocolApplied[0].targetDisease[0].coding[?(@.system=='{Urls.snomed}')].code"
    )
    patient_identifier_value = "contained[?(@.resourceType=='Patient')].identifier[0].value"  # TODO: Fix to use nhs number url lookup
    patient_name_given: str = field(init=False)
    patient_name_family: str = field(init=False)
    patient_birth_date = "contained[?(@.resourceType=='Patient')].birthDate"
    patient_gender = "contained[?(@.resourceType=='Patient')].gender"
    patient_address_postal_code = (
        "contained[?(@.resourceType=='Patient')].address[0].postalCode"
    )
    occurrence_date_time = "occurrenceDateTime"
    organization_identifier_value = (
        "performer[?(@.actor.type=='Organization')].actor.identifier.value"
    )
    organization_identifier_system = (
        "performer[?(@.actor.type=='Organization')].actor.identifier.system"
    )
    organization_display = "performer[?(@.actor.type=='Organization')].actor.display"
    identifier_value = "identifier[0].value"
    identifier_system = "identifier[0].system"
    practitioner_name_given: str = field(init=False)
    practitioner_name_family: str = field(init=False)
    recorded = "recorded"
    primary_source = "primarySource"
    vaccination_procedure_code = generate_field_location_for_extension(
        Urls.vaccination_procedure, Urls.snomed, "code"
    )
    vaccination_procedure_display = generate_field_location_for_extension(
        Urls.vaccination_procedure, Urls.snomed, "display"
    )
    dose_number_positive_int = "protocolApplied[0].doseNumberPositiveInt"
    vaccine_code_coding_code = f"vaccineCode.coding[?(@.system=='{Urls.snomed}')].code"
    vaccine_code_coding_display = (
        f"vaccineCode.coding[?(@.system=='{Urls.snomed}')].display"
    )
    manufacturer_display = "manufacturer.display"
    lot_number = "lotNumber"
    expiration_date = "expirationDate"
    site_coding_code = f"site.coding[?(@.system=='{Urls.snomed}')].code"
    site_coding_display = f"site.coding[?(@.system=='{Urls.snomed}')].display"
    route_coding_code = f"route.coding[?(@.system=='{Urls.snomed}')].code"
    route_coding_display = f"route.coding[?(@.system=='{Urls.snomed}')].display"
    dose_quantity_value = "doseQuantity.value"
    dose_quantity_code = "doseQuantity.code"
    dose_quantity_unit = "doseQuantity.unit"
    location_identifier_value = "location.identifier.value"
    location_identifier_system = "location.identifier.system"

    def set_dynamic_fields(self, imms: dict):
        """Sets the dynamic fields based on the imms dictionary."""
        self.patient_name_given = patient_name_given_field_location(imms)
        self.patient_name_family = patient_name_family_field_location(imms)
        self.practitioner_name_given = practitioner_name_given_field_location(imms)
        self.practitioner_name_family = practitioner_name_family_field_location(imms)
