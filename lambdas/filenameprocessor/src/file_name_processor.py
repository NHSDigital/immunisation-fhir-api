"""
Lambda function for the filenameprocessor lambda. Files received may be from the data sources bucket (for row-by-row
processing) or the config bucket (for uploading to cache).
NOTE: The expected file format for incoming files from the data sources bucket is
'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'. e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv'
(ODS code has multiple lengths)
"""

from uuid import uuid4

from common.ack_file_utils import make_and_upload_ack_file
from common.aws_s3_utils import (
    copy_file_to_external_bucket,
    move_file,
)
from common.batch.audit_table import FILE_DOES_NOT_EXIST_CONDITION_EXPRESSION, create_audit_table_item
from common.clients import STREAM_NAME, get_s3_client, logger
from common.log_decorator import logging_decorator
from common.models.batch_constants import SOURCE_BUCKET_NAME, FileNotProcessedReason, FileStatus
from common.models.errors import UnhandledAuditTableError
from constants import (
    DPS_DESTINATION_BUCKET_NAME,
    DPS_DESTINATION_PREFIX,
    ERROR_TYPE_TO_STATUS_CODE_MAP,
    EXPECTED_DPS_DESTINATION_ACCOUNT,
    EXPECTED_SOURCE_BUCKET_ACCOUNT,
    EXTENDED_ATTRIBUTES_ARCHIVE_PREFIX,
    EXTENDED_ATTRIBUTES_FILE_PREFIX,
)
from file_validation import is_file_in_directory_root, validate_batch_file_key, validate_extended_attributes_file_key
from models.errors import (
    InvalidFileKeyError,
    UnhandledSqsError,
    VaccineTypePermissionsError,
)
from send_sqs_message import make_and_send_sqs_message
from supplier_permissions import validate_permissions_for_extended_attributes_files, validate_vaccine_type_permissions
from utils_for_filenameprocessor import get_creation_and_expiry_times


# NOTE: logging_decorator is applied to handle_record function, rather than lambda_handler, because
# the logging_decorator is for an individual record, whereas the lambda_handler could potentially be handling
# multiple records.
@logging_decorator(prefix="filename_processor", stream_name=STREAM_NAME)
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

    if bucket_name != SOURCE_BUCKET_NAME:
        return handle_unexpected_bucket_name(bucket_name, file_key)

    # In addition to when a batch file is added to the S3 bucket root for processing, this Lambda is also invoked
    # when the file is moved to the processing/ directory and finally the /archive directory. We want to ignore
    # those events. Unfortunately S3 event filtering does not support triggering for root files only. See VED-781
    # for more info.
    if not is_file_in_directory_root(file_key):
        message = "Processing not required. Event was for a file moved to /archive or /processing"
        return {"statusCode": 200, "message": message, "file_key": file_key}

    message_id = str(uuid4())
    s3_response = get_s3_client().get_object(Bucket=bucket_name, Key=file_key)
    created_at_formatted_string, expiry_timestamp = get_creation_and_expiry_times(s3_response)

    if file_key.startswith(EXTENDED_ATTRIBUTES_FILE_PREFIX):
        return handle_extended_attributes_file(
            file_key,
            bucket_name,
            message_id,
            created_at_formatted_string,
            expiry_timestamp,
        )
    else:
        return handle_batch_file(
            file_key,
            bucket_name,
            message_id,
            created_at_formatted_string,
            expiry_timestamp,
        )


def get_file_status_for_error(error: Exception) -> str:
    """Creates a file status based on the type of error that was thrown"""
    if isinstance(error, VaccineTypePermissionsError):
        return f"{FileStatus.NOT_PROCESSED} - {FileNotProcessedReason.UNAUTHORISED}"

    return FileStatus.FAILED


def handle_unexpected_bucket_name(bucket_name: str, file_key: str) -> dict:
    """Handles scenario where Lambda was not invoked by the data-sources bucket. Should not occur due to terraform
    config and overarching design"""
    try:
        if file_key.startswith(EXTENDED_ATTRIBUTES_FILE_PREFIX):
            vaccine_type, organisation_code = validate_extended_attributes_file_key(file_key)
            extended_attribute_identifier = f"{organisation_code}_{vaccine_type}"
            logger.error(
                "Unable to process file %s due to unexpected bucket name %s",
                file_key,
                bucket_name,
            )
            message = f"Failed to process file due to unexpected bucket name {bucket_name}"
            return {
                "statusCode": 500,
                "message": message,
                "file_key": file_key,
                "vaccine_supplier_info": extended_attribute_identifier,
            }
        else:
            vaccine_type, supplier = validate_batch_file_key(file_key)
            logger.error(
                "Unable to process file %s due to unexpected bucket name %s",
                file_key,
                bucket_name,
            )
            message = f"Failed to process file due to unexpected bucket name {bucket_name}"

            return {
                "statusCode": 500,
                "message": message,
                "file_key": file_key,
                "vaccine_type": vaccine_type,
                "supplier": supplier,
            }

    except Exception as error:
        logger.error(
            "Unable to process file due to unexpected bucket name %s and file key %s",
            bucket_name,
            file_key,
        )
        message = f"Failed to process file due to unexpected bucket name {bucket_name} and file key {file_key}"

        return {
            "statusCode": 500,
            "message": message,
            "file_key": file_key,
            "vaccine_type": "unknown",
            "supplier": "unknown",
            "error": str(error),
        }


def handle_batch_file(
    file_key: str, bucket_name: str, message_id: str, created_at_formatted_string: str, expiry_timestamp: int
) -> dict:
    """
    Processes a single record for batch file.
    Returns a dictionary containing information to be included in the logs.
    """
    vaccine_type = "unknown"
    supplier = "unknown"
    try:
        vaccine_type, supplier = validate_batch_file_key(file_key)
        permissions = validate_vaccine_type_permissions(vaccine_type=vaccine_type, supplier=supplier)
        queue_name = f"{supplier}_{vaccine_type}"

        create_audit_table_item(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            queue_name,
            FileStatus.QUEUED,
            condition_expression=FILE_DOES_NOT_EXIST_CONDITION_EXPRESSION,  # Prevents accidental overwrites
        )
        make_and_send_sqs_message(
            file_key,
            message_id,
            permissions,
            vaccine_type,
            supplier,
            created_at_formatted_string,
        )
        logger.info("Lambda invocation successful for file '%s'", file_key)

        return {
            "statusCode": 200,
            "message": "Successfully sent to SQS for further processing",
            "file_key": file_key,
            "message_id": message_id,
            "vaccine_type": vaccine_type,
            "supplier": supplier,
            "queue_name": queue_name,
        }
    except (  # pylint: disable=broad-exception-caught
        VaccineTypePermissionsError,
        InvalidFileKeyError,
        UnhandledAuditTableError,
        UnhandledSqsError,
        Exception,
    ) as error:
        logger.error("Error processing file '%s': %s", file_key, str(error))

        file_status = get_file_status_for_error(error)
        queue_name = f"{supplier}_{vaccine_type}"

        create_audit_table_item(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            queue_name,
            file_status,
            error_details=str(error),
        )

        # Create ack file
        make_and_upload_ack_file(message_id, file_key, False, False, created_at_formatted_string)

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
            "supplier": supplier,
        }


def handle_extended_attributes_file(
    file_key: str, bucket_name: str, message_id: str, created_at_formatted_string: str, expiry_timestamp: int
) -> dict:
    """
    Processes a single record for extended attributes file.
    Returns a dictionary containing information to be included in the logs.
    """

    extended_attribute_identifier = None
    try:
        vaccine_type, organisation_code = validate_extended_attributes_file_key(file_key)
        extended_attribute_identifier = validate_permissions_for_extended_attributes_files(
            vaccine_type, organisation_code
        )

        create_audit_table_item(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            extended_attribute_identifier,
            FileStatus.PROCESSING,
        )

        dest_file_key = f"{DPS_DESTINATION_PREFIX}/{file_key}"
        copy_file_to_external_bucket(
            bucket_name,
            file_key,
            DPS_DESTINATION_BUCKET_NAME,
            dest_file_key,
            EXPECTED_DPS_DESTINATION_ACCOUNT,
            EXPECTED_SOURCE_BUCKET_ACCOUNT,
        )

        move_file(bucket_name, file_key, f"{EXTENDED_ATTRIBUTES_ARCHIVE_PREFIX}/{file_key}")

        create_audit_table_item(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            extended_attribute_identifier,
            FileStatus.PROCESSED,
        )

        return {
            "statusCode": 200,
            "message": "Extended Attributes file successfully processed",
            "file_key": file_key,
            "message_id": message_id,
            "queue_name": extended_attribute_identifier,
        }
    except (  # pylint: disable=broad-exception-caught
        VaccineTypePermissionsError,
        InvalidFileKeyError,
        UnhandledAuditTableError,
        UnhandledSqsError,
        Exception,
    ) as error:
        logger.error("Error processing file '%s': %s", file_key, str(error))

        file_status = get_file_status_for_error(error)

        # NB if we got InvalidFileKeyError we won't have a valid queue name
        if not extended_attribute_identifier:
            extended_attribute_identifier = "unknown"

        # Move file to archive
        move_file(bucket_name, file_key, f"{EXTENDED_ATTRIBUTES_ARCHIVE_PREFIX}/{file_key}")

        create_audit_table_item(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            extended_attribute_identifier,
            file_status,
            error_details=str(error),
        )

        return {
            "statusCode": 500,
            "message": f"Failed to process extended attributes file {file_key} from bucket {bucket_name}",
            "file_key": file_key,
            "message_id": message_id,
            "error": str(error),
        }


def lambda_handler(event: dict, context) -> None:  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda. Processes each record in event records."""

    logger.info("Filename processor lambda task started")

    for record in event["Records"]:
        handle_record(record)

    logger.info("Filename processor lambda task completed")
