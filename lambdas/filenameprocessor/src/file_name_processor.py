"""
Lambda function for the filenameprocessor lambda. Files received may be from the data sources bucket (for row-by-row
processing) or the config bucket (for uploading to cache).
NOTE: The expected file format for incoming files from the data sources bucket is
'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'. e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv'
(ODS code has multiple lengths)
"""

import argparse
from uuid import uuid4

from botocore.exceptions import ClientError

from audit_table import upsert_audit_table
from common.aws_s3_utils import (
    copy_file_to_external_bucket,
    delete_file,
    is_file_in_bucket,
    move_file,
)
from common.clients import STREAM_NAME, get_s3_client, logger
from common.log_decorator import logging_decorator
from common.models.errors import UnhandledAuditTableError
from constants import (
    DPS_DESTINATION_BUCKET_NAME,
    ERROR_TYPE_TO_STATUS_CODE_MAP,
    EXPECTED_BUCKET_OWNER_ACCOUNT,
    EXTENDED_ATTRIBUTES_FILE_PREFIX,
    EXTENDED_ATTRIBUTES_VACC_TYPE,
    SOURCE_BUCKET_NAME,
    FileNotProcessedReason,
    FileStatus,
)
from file_validation import is_file_in_directory_root, validate_batch_file_key, validate_extended_attributes_file_key
from make_and_upload_ack_file import make_and_upload_the_ack_file
from models.errors import (
    InvalidFileKeyError,
    UnhandledSqsError,
    VaccineTypePermissionsError,
)
from send_sqs_message import make_and_send_sqs_message
from supplier_permissions import validate_vaccine_type_permissions
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
            organization_code = validate_extended_attributes_file_key(file_key)
            extended_attribute_identifier = f"{organization_code}_{EXTENDED_ATTRIBUTES_VACC_TYPE}"
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
    file_key: str, bucket_name: str, message_id: str, created_at_formatted_string: str, expiry_timestamp: str
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

        upsert_audit_table(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            queue_name,
            FileStatus.QUEUED,
            condition_expression="attribute_not_exists(message_id)",  # Prevents accidental overwrites
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

        upsert_audit_table(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            queue_name,
            file_status,
            error_details=str(error),
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
            "supplier": supplier,
        }


def handle_extended_attributes_file(
    file_key: str, bucket_name: str, message_id: str, created_at_formatted_string: str, expiry_timestamp: str
) -> dict:
    """
    Processes a single record for extended attributes file.
    Returns a dictionary containing information to be included in the logs.
    """

    # here: the sequence of events should be
    # 1. upsert 'processing'
    # 2. move the file to the dest bucket
    # 3. check the file is present in the dest bucket
    # 4. if it is, delete it from the src bucket, upsert 'processed'
    # 5. if it isn't, move it to the archive/ folder, upsert 'failed'
    # NB for this to work we have to retool upsert so it accepts overwrites, i.e. ignore the ConditionExpression

    try:
        organization_code = validate_extended_attributes_file_key(file_key)
        extended_attribute_identifier = f"{organization_code}_{EXTENDED_ATTRIBUTES_VACC_TYPE}"

        upsert_audit_table(
            message_id,
            file_key,
            created_at_formatted_string,
            expiry_timestamp,
            extended_attribute_identifier,
            FileStatus.PROCESSING,
        )

        dest_file_key = f"dps_destination/{file_key}"
        copy_file_to_external_bucket(
            bucket_name,
            file_key,
            DPS_DESTINATION_BUCKET_NAME,
            dest_file_key,
            EXPECTED_BUCKET_OWNER_ACCOUNT,
            EXPECTED_BUCKET_OWNER_ACCOUNT,
        )
        is_file_in_bucket(DPS_DESTINATION_BUCKET_NAME, dest_file_key)
        delete_file(bucket_name, dest_file_key, EXPECTED_BUCKET_OWNER_ACCOUNT)

        upsert_audit_table(
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
        ClientError,
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
        move_file(bucket_name, file_key, f"archive/{file_key}")

        upsert_audit_table(
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


def run_local():
    parser = argparse.ArgumentParser("file_name_processor")
    parser.add_argument("--bucket", required=True, help="Bucket name.", type=str)
    parser.add_argument("--key", required=True, help="Object key.", type=str)
    args = parser.parse_args()

    event = {"Records": [{"s3": {"bucket": {"name": args.bucket}, "object": {"key": args.key}}}]}
    print(event)
    print(lambda_handler(event=event, context={}))


if __name__ == "__main__":
    run_local()
