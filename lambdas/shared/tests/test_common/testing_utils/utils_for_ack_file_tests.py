"""Utils for the recordprocessor tests"""

from io import StringIO
from unittest.mock import patch

from test_common.testing_utils.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
    BucketNames,
)

# Ensure environment variables are mocked before importing from src files
with patch.dict("os.environ", MOCK_ENVIRONMENT_DICT):
    from csv import DictReader

    from common.clients import REGION_NAME


def get_csv_file_dict_reader(s3_client, bucket_name: str, file_key: str) -> DictReader:
    """Download the file from the S3 bucket and return it as a DictReader"""
    ack_file_csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


class GenericSetUp:
    """
    Performs generic setup of mock resources:
    * If s3_client is provided, creates source, destination and firehose buckets (firehose bucket is used for testing
        only)
    """

    def __init__(
        self,
        s3_client=None,
    ):
        if s3_client:
            for bucket_name in [
                BucketNames.SOURCE,
                BucketNames.DESTINATION,
                BucketNames.MOCK_FIREHOSE,
            ]:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": REGION_NAME},
                )


class GenericTearDown:
    """Performs generic tear down of mock resources"""

    def __init__(
        self,
        s3_client=None,
    ):
        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)
