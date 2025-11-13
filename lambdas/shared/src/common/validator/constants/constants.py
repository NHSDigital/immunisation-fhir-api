class Constants:
    NHS_NUMBER_LENGTH = 10
    PERSON_NAME_ELEMENT_MAX_LENGTH = 35
    GENDERS = ["male", "female", "other", "unknown"]
    DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
    DATETIME_FORMAT = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]
    ALLOWED_SUFFIXES = {
        "+00:00",
        "+01:00",
        "+0000",
        "+0100",
    }
    field_name = "FIELD_TO_REPLACE"

    DATETIME_ERROR_MESSAGE = (
        f"{field_name} must be a valid datetime in one of the following formats:"
        "- 'YYYY-MM-DD' — Full date only"
        "- 'YYYY-MM-DDThh:mm:ss%z' — Full date and time with timezone (e.g. +00:00 or +01:00)"
        "- 'YYYY-MM-DDThh:mm:ss.f%z' — Full date and time with milliseconds and timezone"
        "-  Date must not be in the future."
    )
    STRICT_DATETIME_ERROR_MESSAGE = (
        "Only '+00:00' and '+01:00' are accepted as valid timezone offsets.\n"
        f"Note that partial dates are not allowed for {field_name} in this service.\n"
    )
