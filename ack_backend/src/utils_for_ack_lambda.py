"""Utils for ack lambda"""

from clients import s3_client


def get_row_count(bucket_name: str, file_key: str) -> int:
    """
    Looks in the given bucket and returns the count of the number of lines in the given file.
    NOTE: Blank lines are not included in the count.
    """
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return sum(1 for line in response["Body"].iter_lines() if line.strip())
