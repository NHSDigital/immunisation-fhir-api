"""Constants"""


class Constants:
    """Constants used for the models"""

    STATUSES = ["completed"]
    GENDERS = ["male", "female", "other", "unknown"]
    EXTENSION_URL = ["https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"]
    NOT_DONE_VACCINE_CODES = ["NAVU", "UNC", "UNK", "NA"]
    ALLOWED_KEYS = {
        "Immunization": {
            "resourceType",
            "meta",
            "narrative",
            "contained",
            "id",
            "extension",
            "identifier",
            "status",
            "vaccineCode",
            "patient",
            "occurrenceDateTime",
            "recorded",
            "primarySource",
            "manufacturer",
            "location",
            "lotNumber",
            "expirationDate",
            "site",
            "route",
            "doseQuantity",
            "performer",
            "reasonCode",
            "protocolApplied",
        },
        "Practitioner": {"resourceType", "id", "name"},
        "Patient": {
            "resourceType",
            "id",
            "identifier",
            "name",
            "gender",
            "birthDate",
            "address",
        },
    }

    ALLOWED_CONTAINED_RESOURCES = {"Practitioner", "Patient"}

    # As per Personal Demographics Service FHIR API, the maximum length of a given name element or surname is 35 chars.
    # Given name is a list with a maximum 5 elements. For more info see:
    # https://digital.nhs.uk/developer/api-catalogue/personal-demographics-service-fhir#post-/Patient
    PERSON_NAME_ELEMENT_MAX_LENGTH = 35

    SUPPLIER_PERMISSIONS_KEY = "supplier_permissions"
    VACCINE_TYPE_TO_DISEASES_HASH_KEY = "vacc_to_diseases"
    DISEASES_TO_VACCINE_TYPE_HASH_KEY = "diseases_to_vacc"
