"Upload the content from a config file in S3 to ElastiCache (Redis)"
from clients import s3_client, redis_client


def upload_to_elasticache(file_key: str, bucket_name: str) -> None:
    """Uploads the config file content from S3 to ElastiCache (Redis)."""
    config_file = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    config_file_content = config_file["Body"].read().decode("utf-8")
    # Use the file_key as the Redis key and file content as the value
    redis_client.set(file_key, config_file_content)
