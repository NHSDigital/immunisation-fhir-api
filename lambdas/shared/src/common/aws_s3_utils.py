"""Non-imms Utility Functions"""

from common.clients import get_s3_client, logger


def move_file(bucket_name: str, source_file_key: str, destination_file_key: str) -> None:
    """Moves a file from one location to another within a single S3 bucket by copying and then deleting the file."""
    s3_client = get_s3_client()
    s3_client.copy_object(
        Bucket=bucket_name,
        CopySource={"Bucket": bucket_name, "Key": source_file_key},
        Key=destination_file_key,
    )
    s3_client.delete_object(Bucket=bucket_name, Key=source_file_key)
    logger.info("File moved from %s to %s", source_file_key, destination_file_key)
