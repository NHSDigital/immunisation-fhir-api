"""Utils for filenameprocessor lambda"""

import json
from constants import Constants, SOURCE_BUCKET_NAME, FILE_NAME_PROC_LAMBDA_NAME
from clients import s3_client, logger, lambda_client


def get_created_at_formatted_string(bucket_name: str, file_key: str) -> str:
    """Get the created_at_formatted_string from the response"""
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response["LastModified"].strftime("%Y%m%dT%H%M%S00")


def identify_supplier(ods_code: str) -> str:
    """
    Identifies the supplier from the ods code using the mapping.
    Defaults to empty string if ODS code isn't found in the mappings.
    """
    return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code, "")


def move_file(
    bucket_name: str, source_file_key: str, destination_file_key: str
) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_file_key},
        Key=destination_file_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)


def invoke_filename_lambda(file_key: str, message_id: str) -> None:
    """Invokes the filenameprocessor lambda with the given file key and message id"""
    try:
        lambda_payload = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": SOURCE_BUCKET_NAME},
                        "object": {"key": file_key},
                    },
                    "message_id": message_id,
                }
            ]
        }
        lambda_client.invoke(
            FunctionName=FILE_NAME_PROC_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(lambda_payload),
        )
    except Exception as error:
        logger.error("Error invoking filename lambda: %s", error)
        raise
