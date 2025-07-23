"""
Functions for completing file-level validation
(validating headers and ensuring that the supplier has permission to perform at least one of the requested operations)
"""
from clients import logger, s3_client
from make_and_upload_ack_file import make_and_upload_ack_file
from utils_for_recordprocessor import get_csv_content_dict_reader, invoke_filename_lambda
from errors import InvalidHeaders, NoOperationPermissions
from logging_decorator import file_level_validation_logging_decorator
from audit_table import change_audit_table_status_to_processed, get_next_queued_file_details
from constants import SOURCE_BUCKET_NAME, EXPECTED_CSV_HEADERS, permission_to_operation_map, Permission


def validate_content_headers(csv_content_reader) -> None:
    """Raises an InvalidHeaders error if the headers in the CSV file do not match the expected headers."""
    if csv_content_reader.fieldnames != EXPECTED_CSV_HEADERS:
        raise InvalidHeaders("File headers are invalid.")


def get_permitted_operations(
    supplier: str, vaccine_type: str, allowed_permissions_list: list
) -> set:
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
        permission_to_operation_map[permission].value
        for permission in permissions_for_vaccine_type
    }

    if not permitted_operations_for_vaccine_type:
        raise NoOperationPermissions(
            f"{supplier} does not have permissions to perform any of the requested actions."
        )

    return permitted_operations_for_vaccine_type


def move_file(bucket_name: str, source_file_key: str, destination_file_key: str) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_file_key},
        Key=destination_file_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)


@file_level_validation_logging_decorator
def file_level_validation(incoming_message_body: dict) -> dict:
    """
    Validates that the csv headers are correct and that the supplier has permission to perform at least one of
    the requested operations. Uploades the inf ack file and moves the source file to the processing folder.
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

        # Fetch the data
        csv_reader = get_csv_content_dict_reader(file_key)

        validate_content_headers(csv_reader)

        # Validate has permission to perform at least one of the requested actions
        allowed_operations_set = get_permitted_operations(supplier, vaccine, permission)

        make_and_upload_ack_file(message_id, file_key, True, True, created_at_formatted_string)

        move_file(SOURCE_BUCKET_NAME, file_key, f"processing/{file_key}")

        return {
            "message_id": message_id,
            "vaccine": vaccine,
            "supplier": supplier,
            "file_key": file_key,
            "allowed_operations": allowed_operations_set,
            "created_at_formatted_string": created_at_formatted_string,
            "csv_dict_reader": csv_reader,
        }

    except (InvalidHeaders, NoOperationPermissions, Exception) as error:
        logger.error("Error in file_level_validation: %s", error)

        # NOTE: The Exception may occur before the file_id, file_key and created_at_formatted_string are assigned
        message_id = message_id or "Unable to ascertain message_id"
        file_key = file_key or "Unable to ascertain file_key"
        created_at_formatted_string = created_at_formatted_string or "Unable to ascertain created_at_formatted_string"
        make_and_upload_ack_file(message_id, file_key, False, False, created_at_formatted_string)

        try:
            move_file(SOURCE_BUCKET_NAME, file_key, f"archive/{file_key}")
        except Exception as move_file_error:
            logger.error("Failed to move file to archive: %s", move_file_error)

        # Update the audit table and invoke the filename lambda with next file in the queue (if one exists)
        change_audit_table_status_to_processed(file_key, message_id)
        queue_name = f"{supplier}_{vaccine}"
        next_queued_file_details = get_next_queued_file_details(queue_name)
        if next_queued_file_details:
            invoke_filename_lambda(next_queued_file_details["filename"], next_queued_file_details["message_id"])
        raise
