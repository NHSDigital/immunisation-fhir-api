"""Utils for filenameprocessor lambda"""
from clients import s3_client, logger


def get_created_at_formatted_string(bucket_name: str, file_key: str) -> str:
    """Get the created_at_formatted_string from the response"""
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response["LastModified"].strftime("%Y%m%dT%H%M%S00")


def move_file(bucket_name: str, source_file_key: str, destination_file_key: str) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client.copy_object(
        Bucket=bucket_name, CopySource={"Bucket": bucket_name, "Key": source_file_key}, Key=destination_file_key
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)
