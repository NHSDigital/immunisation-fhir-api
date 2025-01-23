"""
Lambda function for the filenameprocessor lambda. Files received may be from the data sources bucket (for row-by-row
processing) or the config bucket (for uploading to cache).
NOTE: The expected file format for incoming files from the data sources bucket is
'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'. e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv'
(ODS code has multiple lengths)
"""

from uuid import uuid4
from utils_for_filenameprocessor import get_created_at_formatted_string, move_file, invoke_filename_lambda
from file_key_validation import validate_file_key
from send_sqs_message import make_and_send_sqs_message
from make_and_upload_ack_file import make_and_upload_the_ack_file
from audit_table import upsert_audit_table, get_next_queued_file_details, ensure_file_is_not_a_duplicate
from clients import logger
from elasticcache import upload_to_elasticache
from logging_decorator import logging_decorator
from supplier_permissions import validate_vaccine_type_permissions
from errors import (
    VaccineTypePermissionsError,
    InvalidFileKeyError,
    InvalidSupplierError,
    UnhandledAuditTableError,
    DuplicateFileError,
    UnhandledSqsError,
)
from constants import FileStatus, ERROR_TYPE_TO_STATUS_CODE_MAP


# NOTE: logging_decorator is applied to handle_record function, rather than lambda_handler, because
# the logging_decorator is for an individual record, whereas the lambda_handle could potentially be handling
# multiple records.
@logging_decorator
def handle_record(record) -> dict:
    """
    Processes a single record based on whether it came from the 'data-sources' or 'config' bucket.
    Returns a dictionary containing information to be included in the logs.
    """
    try:
        bucket_name = record["s3"]["bucket"]["name"]
        file_key = record["s3"]["object"]["key"]

    except Exception as error:  # pylint: disable=broad-except
        logger.error("Error obtaining file_key: %s", error)
        return {"statusCode": 500, "message": "Failed to download file key", "error": str(error)}

    if "data-sources" in bucket_name and "/" not in file_key:
        try:
            # If the record contains a message_id, then the lambda has been invoked by a file already in the queue
            is_existing_file = "message_id" in record

            # Get message_id if the file is not new, else assign one
            message_id = record.get("message_id", str(uuid4()))

            if not file_key or message_id is None:
                # TODO Update the logger
                logger.info("No files are in queue")

            else:
                created_at_formatted_string = get_created_at_formatted_string(bucket_name, file_key)
                vaccine_type = "unknown"
                supplier = "unknown"
                vaccine_type, supplier = validate_file_key(file_key)
                permissions = validate_vaccine_type_permissions(vaccine_type=vaccine_type, supplier=supplier)
                if not is_existing_file:
                    ensure_file_is_not_a_duplicate(file_key, created_at_formatted_string)

                queue_name = f"{supplier}_{vaccine_type}"
                ready_to_process = upsert_audit_table(
                    message_id,
                    file_key,
                    created_at_formatted_string,
                    queue_name,
                    FileStatus.PROCESSING,
                    is_existing_file,
                )

                if ready_to_process:
                    make_and_send_sqs_message(
                        file_key, message_id, permissions, vaccine_type, supplier, created_at_formatted_string
                    )

                logger.info("File '%s' successfully processed", file_key)

                # Return details for logs
                # TODO Update message
                return {
                    "statusCode": 200,
                    "message": "Successfully sent to SQS queue",
                    "file_key": file_key,
                    "message_id": message_id,
                    "vaccine_type": vaccine_type,
                    "supplier": supplier,
                }

        except (  # pylint: disable=broad-exception-caught
            VaccineTypePermissionsError,
            InvalidFileKeyError,
            InvalidSupplierError,
            UnhandledAuditTableError,
            DuplicateFileError,
            UnhandledSqsError,
            Exception,
        ) as error:
            logger.error("Error processing file '%s': %s", file_key, str(error))

            file_status = FileStatus.DUPLICATE if isinstance(error, DuplicateFileError) else FileStatus.PROCESSED
            queue_name = f"{supplier}_{vaccine_type}"
            upsert_audit_table(
                message_id, file_key, created_at_formatted_string, queue_name, file_status, is_existing_file
            )

            # Create ack file
            # (note that error may have occurred before message_id and created_at_formatted_string were generated)
            message_delivered = False
            if "message_id" not in locals():
                message_id = "Message id was not created"
            if "created_at_formatted_string" not in locals():
                created_at_formatted_string = "created_at_time not identified"
            make_and_upload_the_ack_file(message_id, file_key, message_delivered, created_at_formatted_string)

            # Move file to archive
            move_file(bucket_name, file_key, f"archive/{file_key}")

            # If there is another file waiting in the queue, invoke the filename lambda with the next file
            next_queued_file_details = get_next_queued_file_details(queue_name=f"{supplier}_{vaccine_type}")
            if next_queued_file_details:
                invoke_filename_lambda(next_queued_file_details["filename"], next_queued_file_details["message_id"])

            # Return details for logs
            return {
                "statusCode": ERROR_TYPE_TO_STATUS_CODE_MAP.get(type(error), 500),
                "message": "Infrastructure Level Response Value - Processing Error",
                "file_key": file_key,
                "message_id": message_id,
                "error": str(error),
            }

    elif "config" in bucket_name:
        try:
            upload_to_elasticache(file_key, bucket_name)
            logger.info("%s content successfully uploaded to cache", file_key)
            message = "File content successfully uploaded to cache"
            return {"statusCode": 200, "message": message, "file_key": file_key}
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error uploading to cache for file '%s': %s", file_key, error)
            message = "Failed to upload file content to cache"
            return {"statusCode": 500, "message": message, "file_key": file_key, "error": str(error)}

    else:
        logger.error("Unable to process file %s due to unexpected bucket name %s", file_key, bucket_name)
        message = f"Failed to process file due to unexpected bucket name {bucket_name}"
        return {"statusCode": 500, "message": message, "file_key": file_key}


def lambda_handler(event: dict, context) -> None:  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda. Processes each record in event records."""

    logger.info("Filename processor lambda task started")
    for record in event["Records"]:
        handle_record(record)

    logger.info("Filename processor lambda task completed")
