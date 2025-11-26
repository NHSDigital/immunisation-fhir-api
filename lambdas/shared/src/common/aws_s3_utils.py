"""Non-imms Utility Functions"""

import os

from common.clients import get_s3_client, logger

EXPECTED_BUCKET_OWNER_ACCOUNT = os.getenv("ACCOUNT_ID")
DESTINATION_BUCKET_NAME = os.getenv("DESTINATION_BUCKET_NAME")


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


def move_file_outside_bucket(source_bucket: str, source_key: str, destination_bucket: str, destination_key: str) -> None:
    s3_client = get_s3_client()
    s3_client.copy_object(
        CopySource={"Bucket": source_bucket, "Key": source_key},
        Bucket=destination_bucket,
        Key=destination_key,
        ExpectedBucketOwner=EXPECTED_BUCKET_OWNER_ACCOUNT,
        ExpectedSourceBucketOwner=EXPECTED_BUCKET_OWNER_ACCOUNT,
    )
    s3_client.delete_object(
        Bucket=source_bucket,
        Key=source_key,
        ExpectedBucketOwner=EXPECTED_BUCKET_OWNER_ACCOUNT,
    )
