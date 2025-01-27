"""
Lambda function for the filenameprocessor lambda. Files received may be from the data sources bucket (for row-by-row
processing) or the config bucket (for uploading to cache).
NOTE: The expected file format for incoming files from the data sources bucket is
'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'. e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv'
(ODS code has multiple lengths)
"""

import os
from uuid import uuid4
from utils_for_filenameprocessor import (
    get_created_at_formatted_string,
    move_file,
    invoke_filename_lambda,
)
from file_key_validation import validate_file_key
from send_sqs_message import make_and_send_sqs_message
from make_and_upload_ack_file import make_and_upload_the_ack_file
from audit_table import upsert_audit_table, get_queued_file_details
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

FILE_NAME_PROC_LAMBDA_NAME = os.getenv("FILE_NAME_PROC_LAMBDA_NAME")


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
        return {
            "statusCode": 500,
            "message": "Failed to download file key",
            "error": str(error),
        }

    if "data-sources" in bucket_name and "/" not in file_key:
        try:
            query_type = "create"  # Type of operation on the audit db
            message_id = str(uuid4())  # Assign a unique message_id for the file
            if "message_id" in record:
                message_id = record["message_id"]
                query_type = "update"
            # Get message details
            if file_key and message_id is not None:

                created_at_formatted_string = get_created_at_formatted_string(
                    bucket_name, file_key
                )
                vaccine_type = "unknown"
                supplier = "unknown"
                vaccine_type, supplier = validate_file_key(file_key)
                permissions = validate_vaccine_type_permissions(
                    vaccine_type=vaccine_type, supplier=supplier
                )
                # Process the file
                # TODO rename to add clarity
                status = True  # Based on the status the file will be forwarded to sqs fifo queue.
                status = upsert_audit_table(
                    message_id,
                    file_key,
                    created_at_formatted_string,
                    f"{supplier}_{vaccine_type}",
                    "Processing",
                    query_type,
                )
                if status:
                    make_and_send_sqs_message(
                        file_key,
                        message_id,
                        permissions,
                        vaccine_type,
                        supplier,
                        created_at_formatted_string,
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
            else:
                # TODO Update the logger
                logger.info("No files are in queue")

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
            # Process the file if the error is not of type Duplicate since it is already updated in audit table
            if not isinstance(error, DuplicateFileError):
                upsert_audit_table(
                    message_id,
                    file_key,
                    created_at_formatted_string,
                    f"{supplier}_{vaccine_type}",
                    "Processed",
                    query_type,
                )
            # Create ack file
            # (note that error may have occurred before message_id and created_at_formatted_string were generated)
            message_delivered = False
            if "message_id" not in locals():
                message_id = "Message id was not created"
            if "created_at_formatted_string" not in locals():
                created_at_formatted_string = "created_at_time not identified"
            make_and_upload_the_ack_file(
                message_id, file_key, message_delivered, created_at_formatted_string
            )
            destination_key = f"archive/{file_key}"
            move_file(bucket_name, file_key, destination_key)
            # Following code will get executed in case of duplicate scenario, vaccine permission error, etc
            file_key, message_id = get_queued_file_details(f"{supplier}_{vaccine_type}")
            if file_key and message_id is not None:
                invoke_filename_lambda(
                    FILE_NAME_PROC_LAMBDA_NAME, bucket_name, file_key, message_id
                )

            status_code_map = {
                VaccineTypePermissionsError: 403,
                InvalidFileKeyError: 400,  # Includes invalid ODS code, therefore unable to identify supplier
                InvalidSupplierError: 500,  # Only raised if supplier variable is not correctly set
                UnhandledAuditTableError: 500,
                DuplicateFileError: 422,
                UnhandledSqsError: 500,
                Exception: 500,
            }

            # Return details for logs
            return {
                "statusCode": status_code_map.get(type(error), 500),
                "message": "Infrastructure Level Response Value - Processing Error",
                "file_key": file_key,
                "message_id": message_id,
                "error": str(error),
            }

    elif "config" in bucket_name:
        try:
            upload_to_elasticache(file_key, bucket_name)
            logger.info("%s content successfully uploaded to cache", file_key)
            return {
                "statusCode": 200,
                "message": "File content successfully uploaded to cache",
                "file_key": file_key,
            }
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error uploading to cache for file '%s': %s", file_key, error)
            return {
                "statusCode": 500,
                "message": "Failed to upload file content to cache",
                "file_key": file_key,
                "error": str(error),
            }

    else:
        logger.error(
            "Unable to process file %s due to unexpected bucket name %s",
            file_key,
            bucket_name,
        )
        return {
            "statusCode": 500,
            "message": f"Failed to process file due to unexpected bucket name {bucket_name}",
            "file_key": file_key,
        }


def lambda_handler(event: dict, context) -> None:  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda. Processes each record in event records."""

    logger.info("Filename processor lambda task started")
    for record in event["Records"]:
        handle_record(record)

    logger.info("Filename processor lambda task completed")
