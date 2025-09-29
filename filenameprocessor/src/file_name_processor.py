"""
Lambda function for the filenameprocessor lambda. Files received may be from the data sources bucket (for row-by-row
processing) or the config bucket (for uploading to cache).
NOTE: The expected file format for incoming files from the data sources bucket is
'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'. e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv'
(ODS code has multiple lengths)
"""

import argparse
from uuid import uuid4
from utils_for_filenameprocessor import get_creation_and_expiry_times, move_file
from file_validation import validate_file_key, is_file_in_directory_root
from send_sqs_message import make_and_send_sqs_message
from make_and_upload_ack_file import make_and_upload_the_ack_file
from audit_table import upsert_audit_table
from clients import logger, s3_client
from logging_decorator import logging_decorator
from supplier_permissions import validate_vaccine_type_permissions
from errors import (
    VaccineTypePermissionsError,
    InvalidFileKeyError,
    UnhandledAuditTableError,
    UnhandledSqsError
)
from constants import FileNotProcessedReason, FileStatus, ERROR_TYPE_TO_STATUS_CODE_MAP, SOURCE_BUCKET_NAME


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
    expiry_timestamp = "unknown"

    if bucket_name != SOURCE_BUCKET_NAME:
        return handle_unexpected_bucket_name(bucket_name, file_key)

    # In addition to when a batch file is added to the S3 bucket root for processing, this Lambda is also invoked
    # when the file is moved to the processing/ directory and finally the /archive directory. We want to ignore
    # those events. Unfortunately S3 event filtering does not support triggering for root files only. See VED-781
    # for more info.
    if not is_file_in_directory_root(file_key):
        message = "Processing not required. Event was for a file moved to /archive or /processing"
        return {"statusCode": 200, "message": message, "file_key": file_key}

    # Set default values for file-specific variables
    message_id = "Message id was not created"
    created_at_formatted_string = "created_at_time not identified"

    try:
        message_id = str(uuid4())
        s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        created_at_formatted_string, expiry_timestamp = get_creation_and_expiry_times(s3_response)

        vaccine_type, supplier = validate_file_key(file_key)
        permissions = validate_vaccine_type_permissions(vaccine_type=vaccine_type, supplier=supplier)

        queue_name = f"{supplier}_{vaccine_type}"
        upsert_audit_table(
            message_id, file_key, created_at_formatted_string, expiry_timestamp, queue_name, FileStatus.QUEUED
        )
        make_and_send_sqs_message(
            file_key, message_id, permissions, vaccine_type, supplier, created_at_formatted_string
        )

        logger.info("Lambda invocation successful for file '%s'", file_key)

        # Return details for logs
        return {
            "statusCode": 200,
            "message": "Successfully sent to SQS for further processing",
            "file_key": file_key,
            "message_id": message_id,
            "vaccine_type": vaccine_type,
            "supplier": supplier,
        }

    except (  # pylint: disable=broad-exception-caught
        VaccineTypePermissionsError,
        InvalidFileKeyError,
        UnhandledAuditTableError,
        UnhandledSqsError,
        Exception,
    ) as error:
        logger.error("Error processing file '%s': %s", file_key, str(error))

        queue_name = f"{supplier}_{vaccine_type}"
        file_status = get_file_status_for_error(error)

        upsert_audit_table(
            message_id, file_key, created_at_formatted_string, expiry_timestamp, queue_name, file_status,
            error_details=str(error)
        )

        # Create ack file
        message_delivered = False
        make_and_upload_the_ack_file(message_id, file_key, message_delivered, created_at_formatted_string)

        # Move file to archive
        move_file(bucket_name, file_key, f"archive/{file_key}")

        # Return details for logs
        return {
            "statusCode": ERROR_TYPE_TO_STATUS_CODE_MAP.get(type(error), 500),
            "message": "Infrastructure Level Response Value - Processing Error",
            "file_key": file_key,
            "message_id": message_id,
            "error": str(error),
            "vaccine_type": vaccine_type,
            "supplier": supplier
        }


def get_file_status_for_error(error: Exception) -> str:
    """Creates a file status based on the type of error that was thrown"""
    if isinstance(error, VaccineTypePermissionsError):
        return f"{FileStatus.NOT_PROCESSED} - {FileNotProcessedReason.UNAUTHORISED}"

    return FileStatus.FAILED


def handle_unexpected_bucket_name(bucket_name: str, file_key: str) -> dict:
    """Handles scenario where Lambda was not invoked by the data-sources bucket. Should not occur due to terraform
    config and overarching design"""
    try:
        vaccine_type, supplier = validate_file_key(file_key)
        logger.error("Unable to process file %s due to unexpected bucket name %s", file_key, bucket_name)
        message = f"Failed to process file due to unexpected bucket name {bucket_name}"

        return {"statusCode": 500, "message": message, "file_key": file_key,
                "vaccine_type": vaccine_type, "supplier": supplier}

    except Exception as error:
        logger.error("Unable to process file due to unexpected bucket name %s and file key %s",
                     bucket_name, file_key)
        message = f"Failed to process file due to unexpected bucket name {bucket_name} and file key {file_key}"

        return {"statusCode": 500, "message": message, "file_key": file_key,
                "vaccine_type": "unknown", "supplier": "unknown", "error": str(error)}


def lambda_handler(event: dict, context) -> None:  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda. Processes each record in event records."""

    logger.info("Filename processor lambda task started")

    for record in event["Records"]:
        handle_record(record)

    logger.info("Filename processor lambda task completed")


def run_local():
    parser = argparse.ArgumentParser("file_name_processor")
    parser.add_argument("--bucket", required=True, help="Bucket name.", type=str)
    parser.add_argument("--key", required=True, help="Object key.", type=str)
    args = parser.parse_args()

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": args.bucket},
                    "object": {"key": args.key}
                }
            }
        ]
    }
    print(event)
    print(lambda_handler(event=event, context={}))


if __name__ == "__main__":
    run_local()
