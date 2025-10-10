"""Functions for file key validation"""

from re import match
from datetime import datetime
from constants import VALID_VERSIONS
from elasticache import (
    get_valid_vaccine_types_from_cache,
    get_supplier_system_from_cache,
)
from errors import InvalidFileKeyError


def is_file_in_directory_root(file_key: str) -> bool:
    """ "
    Checks that a given file is in the bucket root rather than a child directory e.g. archive/xyz.csv
    """
    return "/" not in file_key


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

    if not match(r"^[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*", file_key):
        raise InvalidFileKeyError("Initial file validation failed: invalid file key format")

    file_key = file_key.upper()
    file_name_and_extension = file_key.rsplit(".", 1)

    if len(file_name_and_extension) != 2:
        raise InvalidFileKeyError("Initial file validation failed: missing file extension")

    file_key_parts_without_extension = file_name_and_extension[0].split("_")

    vaccine_type = file_key_parts_without_extension[0]
    vaccination = file_key_parts_without_extension[1]
    version = file_key_parts_without_extension[2]
    ods_code = file_key_parts_without_extension[3]
    timestamp = file_key_parts_without_extension[4]
    extension = file_name_and_extension[1]
    supplier = get_supplier_system_from_cache(ods_code)

    valid_vaccine_types = get_valid_vaccine_types_from_cache()

    # Validate each file key element
    if not (
        vaccine_type in valid_vaccine_types
        and vaccination == "VACCINATIONS"
        and version in VALID_VERSIONS
        and supplier  # Note that if supplier could be identified, this also implies that ODS code is valid
        and is_valid_datetime(timestamp)
        and ((extension == "CSV") or (extension == "DAT"))  # The DAT extension has been added for MESH file processing
    ):
        raise InvalidFileKeyError("Initial file validation failed: invalid file key")

    return vaccine_type, supplier
