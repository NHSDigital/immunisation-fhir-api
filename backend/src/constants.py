"""Constants"""

# Constants for use within the test
VALID_NHS_NUMBER = "1345678940"  # Valid for pre, FHIR and post validators
NHS_NUMBER_USED_IN_SAMPLE_DATA = "9000000009"
ADDRESS_UNKNOWN_POSTCODE = "ZZ99 3WZ"


class Urls:
    """Urls which are expected to be used within the FHIR Immunization Resource json data"""

    nhs_number = "https://fhir.nhs.uk/Id/nhs-number"
    vaccination_procedure = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    snomed = "http://snomed.info/sct"
    nhs_number_verification_status_structure_definition = (
        "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
    )
    nhs_number_verification_status_code_system = (
        "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
    )
    ods_organization_code = "https://fhir.nhs.uk/Id/ods-organization-code"
    urn_school_number = "https://fhir.hl7.org.uk/Id/urn-school-number"
