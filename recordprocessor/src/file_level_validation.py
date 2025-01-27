"""
Functions for completing file-level validation
(validating headers and ensuring that the supplier has permission to perform at least one of the requested operations)
"""

import os
from constants import Constants
from unique_permission import get_unique_action_flags_from_s3
from clients import logger, s3_client
from make_and_upload_ack_file import make_and_upload_ack_file
from mappings import Vaccine
from utils_for_recordprocessor import (
    get_csv_content_dict_reader,
    invoke_filename_lambda,
)
from errors import InvalidHeaders, NoOperationPermissions
from logging_decorator import file_level_validation_logging_decorator
from audit_table import update_audit_table_status, get_queued_file_details

# TODO Move to constants
SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
FILE_NAME_PROC_LAMBDA_NAME = os.getenv("FILE_NAME_PROC_LAMBDA_NAME")


def validate_content_headers(csv_content_reader) -> None:
    """Raises an InvalidHeaders error if the headers in the CSV file do not match the expected headers."""
    if csv_content_reader.fieldnames != Constants.expected_csv_headers:
        raise InvalidHeaders("File headers are invalid.")


def validate_action_flag_permissions(
    supplier: str, vaccine_type: str, allowed_permissions_list: list, csv_data: str
) -> set:
    """
    Validates that the supplier has permission to perform at least one of the requested operations for the given
    vaccine type and returns the set of allowed operations for that vaccine type.
    Raises a NoPermissionsError if the supplier does not have permission to perform any of the requested operations.
    """
    # If the supplier has full permissions for the vaccine type, return True
    if f"{vaccine_type}_FULL" in allowed_permissions_list:
        return {"CREATE", "UPDATE", "DELETE"}

    # Get unique ACTION_FLAG values from the S3 file
    operations_requested = get_unique_action_flags_from_s3(csv_data)

    # Convert action flags into the expected operation names
    requested_permissions_set = {
        f"{vaccine_type}_{'CREATE' if action == 'NEW' else action}"
        for action in operations_requested
    }

    # Check if any of the CSV permissions match the allowed permissions
    if not requested_permissions_set.intersection(allowed_permissions_list):
        raise NoOperationPermissions(
            f"{supplier} does not have permissions to perform any of the requested actions."
        )

    logger.info(
        "%s permissions %s match one of the requested permissions required to %s",
        supplier,
        allowed_permissions_list,
        requested_permissions_set,
    )
    return {
        perm.split("_")[1].upper()
        for perm in allowed_permissions_list
        if perm.startswith(vaccine_type)
    }


@file_level_validation_logging_decorator
def file_level_validation(incoming_message_body: dict) -> None:
    """Validates that the csv headers are correct and that the supplier has permission to perform at least one of
    the requested operations. Returns an interim message body for row level processing.
    """
    try:
        message_id = incoming_message_body.get("message_id")
        vaccine: Vaccine = next(  # Convert vaccine_type to Vaccine enum
            vaccine
            for vaccine in Vaccine
            if vaccine.value == incoming_message_body.get("vaccine_type").upper()
        )
        supplier = incoming_message_body.get("supplier").upper()
        file_key = incoming_message_body.get("filename")
        permission = incoming_message_body.get("permission")
        created_at_formatted_string = incoming_message_body.get(
            "created_at_formatted_string"
        )

        # Fetch the data
        csv_reader, csv_data = get_csv_content_dict_reader(file_key)

        try:
            validate_content_headers(csv_reader)

            # Validate has permission to perform at least one of the requested actions
            allowed_operations_set = validate_action_flag_permissions(
                supplier, vaccine.value, permission, csv_data
            )
        except (InvalidHeaders, NoOperationPermissions):
            make_and_upload_ack_file(
                message_id, file_key, False, False, created_at_formatted_string
            )
            raise

        # Initialise the accumulated_ack_file_content with the headers
        make_and_upload_ack_file(
            message_id, file_key, True, True, created_at_formatted_string
        )
        destination_key = f"processing/{file_key}"
        move_file(SOURCE_BUCKET_NAME, file_key, destination_key)
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
        created_at_formatted_string = (
            created_at_formatted_string
            or "Unable to ascertain created_at_formatted_string"
        )
        make_and_upload_ack_file(
            message_id, file_key, False, False, created_at_formatted_string
        )
        destination_key = f"archive/{file_key}"
        move_file(SOURCE_BUCKET_NAME, file_key, destination_key)
        # Following code excutes on failure to update audit.
        queue_name = update_audit_table_status(file_key)
        file_key, message_id = get_queued_file_details(queue_name)
        if file_key and message_id is not None:
            invoke_filename_lambda(
                FILE_NAME_PROC_LAMBDA_NAME, SOURCE_BUCKET_NAME, file_key, message_id
            )
        raise


def move_file(bucket_name: str, source_key: str, destination_key: str) -> None:
    """Moves a file from one location to another in S3 by copying and then deleting it.     Args:
    bucket_name (str): Name of the S3 bucket.         source_key (str): Source file key.
    destination_key (str): Destination file key."""
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_key},
        Key=destination_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_key)
    logger.info("File moved from %s to %s", source_key, destination_key)
