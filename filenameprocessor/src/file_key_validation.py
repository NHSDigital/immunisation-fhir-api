"""Functions for file key validation"""

from re import match
from datetime import datetime
from constants import Constants
from utils_for_filenameprocessor import identify_supplier
from errors import InvalidFileKeyError


def is_valid_datetime(timestamp: str) -> bool:
    """
    Returns a bool to indicate whether the timestamp is a valid datetime in the format 'YYYYmmddTHHMMSSzz'
    where 'zz' is a two digit number indicating the timezone
    """
    # Check that datetime (excluding timezone) is a valid datetime in the expected format.
    if len(timestamp) < 15:
        return False

    # Note that any digits after the seconds (i.e. from the 16th character onwards, usually expected to represent
    # timezone), do not need to be validated
    try:
        datetime.strptime(timestamp[:15], "%Y%m%dT%H%M%S")
    except ValueError:
        return False

    return True


def validate_file_key(file_key: str) -> tuple[str, str]:
    """
    Checks that all elements of the file key are valid, raises an exception otherwise.
    Returns a tuple containing the vaccine_type and supplier (both converted to upper case).
    """

    if not match(r"^[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*\.[^_.]*$", file_key):
        error_message = "Initial file validation failed: invalid file key format"
        raise InvalidFileKeyError(error_message)

    file_key = file_key.upper()
    file_key_parts_without_extension = file_key.split(".")[0].split("_")

    vaccine_type = file_key_parts_without_extension[0]
    vaccination = file_key_parts_without_extension[1]
    version = file_key_parts_without_extension[2]
    ods_code = file_key_parts_without_extension[3]
    timestamp = file_key_parts_without_extension[4]
    extension = file_key.split(".")[1]
    supplier = identify_supplier(ods_code)

    # Validate each file key element
    if not (
        vaccine_type in Constants.VALID_VACCINE_TYPES
        and vaccination == "VACCINATIONS"
        and version in Constants.VALID_VERSIONS
        and supplier  # Note that if supplier could be identified, this also implies that ODS code is valid
        and is_valid_datetime(timestamp)
        and ((extension == "CSV") or (extension == "DAT"))  # The DAT extension has been added for MESH file processing
    ):
        raise InvalidFileKeyError("Initial file validation failed: invalid file key")

    return vaccine_type, supplier
