"""Functions for file key validation"""

from datetime import datetime
from re import match

from constants import EXTENDED_ATTRIBUTES_FILE_PREFIX, VALID_EA_VERSIONS, VALID_VERSIONS
from elasticache import (
    get_supplier_system_from_cache,
    get_valid_vaccine_types_from_cache,
)
from models.errors import InvalidFileKeyError


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


def validate_extended_attributes_file_key(file_key: str) -> str:
    """
    Checks that all elements of the file key are valid, raises an exception otherwise.
    Returns a string containing the organization code.
    """
    if not match(r"^[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*", file_key):
        raise InvalidFileKeyError("Initial file validation failed: invalid extended attributes file key format")

    file_key_parts_without_extension, extension = split_file_key(file_key)
    file_type = "_".join(file_key_parts_without_extension[:3])
    version = "_".join(file_key_parts_without_extension[3:5])
    organization_code = file_key_parts_without_extension[5]
    timestamp = file_key_parts_without_extension[6]
    supplier = get_supplier_system_from_cache(organization_code)
    valid_vaccine_types = get_valid_vaccine_types_from_cache()
    vaccine_type = "COVID"

    if not (
        vaccine_type in valid_vaccine_types
        and file_type == EXTENDED_ATTRIBUTES_FILE_PREFIX.upper()
        and version == VALID_EA_VERSIONS
        and supplier  # Note that if supplier could be identified, this also implies that ODS code is valid
        and is_valid_datetime(timestamp)
        and (
            (extension == "CSV") or (extension == "DAT") or (extension == "CTL")
        )  # The DAT extension has been added for MESH file processing
    ):
        raise InvalidFileKeyError("Initial file validation failed: invalid file key")

    return organization_code


def validate_batch_file_key(file_key: str) -> tuple[str, str]:
    """
    Checks that all elements of the file key are valid, raises an exception otherwise.
    Returns a tuple containing the vaccine_type and supplier (both converted to upper case).
    """

    if not match(r"^[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*", file_key):
        raise InvalidFileKeyError("Initial file validation failed: invalid file key format")

    file_key_parts_without_extension, file_name_and_extension = split_file_key(file_key)

    vaccine_type = file_key_parts_without_extension[0]
    vaccination = file_key_parts_without_extension[1]
    version = file_key_parts_without_extension[2]
    ods_code = file_key_parts_without_extension[3]
    timestamp = file_key_parts_without_extension[4]
    extension = file_name_and_extension
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


def split_file_key(file_key: str) -> tuple[list[str], str]:
    file_key = file_key.upper()
    file_name_and_extension = file_key.rsplit(".", 1)

    if len(file_name_and_extension) != 2:
        raise InvalidFileKeyError("Initial file validation failed: missing file extension")

    return file_name_and_extension[0].split("_"), file_name_and_extension[1]
