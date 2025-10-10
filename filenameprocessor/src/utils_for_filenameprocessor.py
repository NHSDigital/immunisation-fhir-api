"""Utils for filenameprocessor lambda"""

from datetime import timedelta
from clients import s3_client, logger
from constants import AUDIT_TABLE_TTL_DAYS


def get_creation_and_expiry_times(s3_response: dict) -> (str, int):
    """Get 'created_at_formatted_string' and 'expires_at' from the response"""
    creation_datetime = s3_response["LastModified"]
    expiry_datetime = creation_datetime + timedelta(days=int(AUDIT_TABLE_TTL_DAYS))
    expiry_timestamp = int(expiry_datetime.timestamp())
    return creation_datetime.strftime("%Y%m%dT%H%M%S00"), expiry_timestamp


def move_file(bucket_name: str, source_file_key: str, destination_file_key: str) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_file_key},
        Key=destination_file_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)
