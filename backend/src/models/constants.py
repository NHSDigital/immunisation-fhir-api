"""Constants"""


class Constants:
    """Constants used for the models"""    
    STATUSES = ["completed"]
    GENDERS = ["male", "female", "other", "unknown"]
    NOT_DONE_VACCINE_CODES = ["NAVU", "UNC", "UNK", "NA"]
    allowed_keys = {
    "Immunization": {
        "resourceType", "contained", "extension", "identifier", "status", "vaccineCode",
        "patient", "occurrenceDateTime", "recorded", "primarySource", "manufacturer",
        "location", "lotNumber", "expirationDate", "site", "route", "doseQuantity",
        "performer", "reasonCode", "protocolApplied"
    },
    "Practitioner": {
        "resourceType", "id", "name"
    },
    "Patient": {
        "resourceType", "id", "identifier", "name", "gender", "birthDate", "address"
    }
}
    allowed_keys_with_id = {
    "Immunization": {
        "resourceType", "contained", "id","extension", "identifier", "status", "vaccineCode",
        "patient", "occurrenceDateTime", "recorded", "primarySource", "manufacturer",
        "location", "lotNumber", "expirationDate", "site", "route", "doseQuantity",
        "performer", "reasonCode", "protocolApplied"
    }
}

    allowed_contained_resources = {"Practitioner", "Patient"}
