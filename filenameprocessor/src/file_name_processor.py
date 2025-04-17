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
from elasticache import upload_to_elasticache
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
# the logging_decorator is for an individual record, whereas the lambda_handler could potentially be handling
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

    vaccine_type = "unknown"
    supplier = "unknown"

    if "data-sources" in bucket_name:

        # The lambda is unintentionally invoked when a file is moved into a different folder in the source bucket.
        # Excluding file keys containing a "/" is a workaround to prevent the lambda from processing files that
        # are not in the root of the source bucket.
        if "/" in file_key:
            message = "File skipped due to duplicate lambda invoaction"
            return {"statusCode": 200, "message": message, "file_key": file_key}

        # Set default values for file-specific variables
        message_id = "Message id was not created"
        created_at_formatted_string = "created_at_time not identified"

        try:
            # If the record contains a message_id, then the lambda has been invoked by a file already in the queue
            is_existing_file = "message_id" in record

            # Get message_id if the file is not new, else assign one
            message_id = record.get("message_id", str(uuid4()))

            vaccine_type, supplier = validate_file_key(file_key)

            created_at_formatted_string = get_created_at_formatted_string(bucket_name, file_key)

            permissions = validate_vaccine_type_permissions(vaccine_type=vaccine_type, supplier=supplier)
            if not is_existing_file:
                ensure_file_is_not_a_duplicate(file_key, created_at_formatted_string)

            queue_name = f"{supplier}_{vaccine_type}"
            file_status_is_queued = upsert_audit_table(
                message_id, file_key, created_at_formatted_string, queue_name, FileStatus.PROCESSING, is_existing_file
            )

            if file_status_is_queued:
                message_for_logs = "File is successfully queued for processing"
            else:
                make_and_send_sqs_message(
                    file_key, message_id, permissions, vaccine_type, supplier, created_at_formatted_string
                )
                message_for_logs = "Successfully sent to SQS for further processing"

            logger.info("Lambda invocation successful for file '%s'", file_key)

            # Return details for logs
            return {
                "statusCode": 200,
                "message": message_for_logs,
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
            message_delivered = False
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
            return {"statusCode": 500, "message": message, "file_key": file_key, "error": str(error),
                    "vaccine_type": vaccine_type, "supplier": supplier}

    else:
        logger.error("Unable to process file %s due to unexpected bucket name %s", file_key, bucket_name)
        message = f"Failed to process file due to unexpected bucket name {bucket_name}"

        return {"statusCode": 500, "message": message, "file_key": file_key,
                "vaccine_type": vaccine_type, "supplier": supplier}


def lambda_handler(event: dict, context) -> None:  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda. Processes each record in event records."""

    logger.info("Filename processor lambda task started")
    for record in event["Records"]:
        handle_record(record)

    logger.info("Filename processor lambda task completed")


if __name__ == "__main__":

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "immunisation-batch-internal-dev-data-sources"
                    },
                    "object": {
                        "key": "FLU_Vaccinations_v5_YGM41_20000101T00000001.csv"
                    }
                }
            }
        ]
    }
    print(event)
    print(lambda_handler(event=event, context={}))
