"""Constants"""


class Constants:
    """Constants used for the models"""    
    STATUSES = ["completed"]
    GENDERS = ["male", "female", "other", "unknown"]
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
        "Patient": {"resourceType", "id", "identifier", "name", "gender", "birthDate", "address"},
    }

    ALLOWED_CONTAINED_RESOURCES = {"Practitioner", "Patient"}
