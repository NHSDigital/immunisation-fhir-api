"""
Functions for completing file-level validation
(validating headers and ensuring that the supplier has permission to perform at least one of the requested operations)
"""

from csv import DictReader

from audit_table import update_audit_table_status
from common.clients import logger
from common.utils import move_file
from constants import (
    ARCHIVE_DIR_NAME,
    EXPECTED_CSV_HEADERS,
    PROCESSING_DIR_NAME,
    SOURCE_BUCKET_NAME,
    FileNotProcessedReason,
    FileStatus,
    Permission,
    permission_to_operation_map,
)
from logging_decorator import file_level_validation_logging_decorator
from make_and_upload_ack_file import make_and_upload_ack_file
from models.errors import InvalidHeaders, NoOperationPermissions
from utils_for_recordprocessor import get_csv_content_dict_reader


def validate_content_headers(csv_content_reader: DictReader) -> None:
    """Raises an InvalidHeaders error if the headers in the CSV file do not match the expected headers."""
    if csv_content_reader.fieldnames != EXPECTED_CSV_HEADERS:
        raise InvalidHeaders("File headers are invalid.")


def file_is_empty(row_count: int) -> bool:
    """Simple helper for readability to check if no rows were processed in a file i.e. empty"""
    return row_count == 0


def get_permitted_operations(supplier: str, vaccine_type: str, allowed_permissions_list: list) -> set:
    # Check if supplier has permission for the subject vaccine type and extract permissions
    permission_strs_for_vaccine_type = {
        permission_str
        for permission_str in allowed_permissions_list
        if permission_str.split(".")[0].upper() == vaccine_type.upper()
    }

    # Extract permissions letters to get map key from the allowed vaccine type
    permissions_for_vaccine_type = {
        Permission(permission)
        for permission_str in permission_strs_for_vaccine_type
        for permission in permission_str.split(".")[1].upper()
        if permission in list(Permission)
    }

    # Map Permission key to action flag
    permitted_operations_for_vaccine_type = {
        permission_to_operation_map[permission].value for permission in permissions_for_vaccine_type
    }

    if not permitted_operations_for_vaccine_type:
        raise NoOperationPermissions(f"{supplier} does not have permissions to perform any of the requested actions.")

    return permitted_operations_for_vaccine_type


@file_level_validation_logging_decorator
def file_level_validation(incoming_message_body: dict) -> dict:
    """
    Validates that the csv headers are correct and that the supplier has permission to perform at least one of
    the requested operations. Uploads the inf ack file and moves the source file to the processing folder.
    Returns an interim message body for row level processing.
    NOTE: If file level validation fails the source file is moved to the archive folder, the audit table is updated
    to reflect the file has been processed and the filename lambda is invoked with the next file in the queue.
    """
    try:
        message_id = incoming_message_body.get("message_id")
        vaccine = incoming_message_body.get("vaccine_type").upper()
        supplier = incoming_message_body.get("supplier").upper()
        file_key = incoming_message_body.get("filename")
        permission = incoming_message_body.get("permission")
        created_at_formatted_string = incoming_message_body.get("created_at_formatted_string")
        encoder = incoming_message_body.get("encoder", "utf-8")

        # Fetch the data
        try:
            csv_reader = get_csv_content_dict_reader(file_key, encoder=encoder)
            validate_content_headers(csv_reader)
        except UnicodeDecodeError as e:
            logger.warning("Invalid Encoding detected: %s", e)
            # retry with cp1252 encoding
            csv_reader = get_csv_content_dict_reader(file_key, encoder="cp1252")
            validate_content_headers(csv_reader)

        # Validate has permission to perform at least one of the requested actions
        allowed_operations_set = get_permitted_operations(supplier, vaccine, permission)

        make_and_upload_ack_file(message_id, file_key, True, True, created_at_formatted_string)

        move_file(SOURCE_BUCKET_NAME, file_key, f"{PROCESSING_DIR_NAME}/{file_key}")

        return {
            "message_id": message_id,
            "vaccine": vaccine,
            "supplier": supplier,
            "file_key": file_key,
            "allowed_operations": allowed_operations_set,
            "created_at_formatted_string": created_at_formatted_string,
            "csv_dict_reader": csv_reader,
        }

    except Exception as error:
        logger.error("Error in file_level_validation: %s", error)

        # NOTE: The Exception may occur before the file_id, file_key and created_at_formatted_string are assigned
        message_id = message_id or "Unable to ascertain message_id"
        file_key = file_key or "Unable to ascertain file_key"
        created_at_formatted_string = created_at_formatted_string or "Unable to ascertain created_at_formatted_string"
        make_and_upload_ack_file(message_id, file_key, False, False, created_at_formatted_string)
        file_status = (
            f"{FileStatus.NOT_PROCESSED} - {FileNotProcessedReason.UNAUTHORISED}"
            if isinstance(error, NoOperationPermissions)
            else FileStatus.FAILED
        )

        try:
            move_file(SOURCE_BUCKET_NAME, file_key, f"{ARCHIVE_DIR_NAME}/{file_key}")
        except Exception as move_file_error:
            logger.error("Failed to move file to archive: %s", move_file_error)

        # Update the audit table
        update_audit_table_status(file_key, message_id, file_status, error_details=str(error))
        raise
