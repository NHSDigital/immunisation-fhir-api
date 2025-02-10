"""Generic setup and teardown for ACK backend tests"""

from tests.utils_for_ack_backend_tests.mock_environment_variables import BucketNames, Firehose, REGION_NAME


class GenericSetUp:
    """
    Performs generic setup of mock resources:
    * If s3_client is provided, creates source, destination and firehose buckets (firehose bucket is used for testing
        only)
    * If firehose_client is provided, creates a firehose delivery stream
    """

    def __init__(self, s3_client=None, firehose_client=None):

        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION, BucketNames.MOCK_FIREHOSE]:
                s3_client.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": REGION_NAME}
                )

        if firehose_client:
            firehose_client.create_delivery_stream(
                DeliveryStreamName=Firehose.STREAM_NAME,
                DeliveryStreamType="DirectPut",
                S3DestinationConfiguration={
                    "RoleARN": "arn:aws:iam::123456789012:role/mock-role",
                    "BucketARN": "arn:aws:s3:::" + BucketNames.MOCK_FIREHOSE,
                    "Prefix": "firehose-backup/",
                },
            )


class GenericTearDown:
    """Performs generic tear down of mock resources"""

    def __init__(self, s3_client=None, firehose_client=None):

        if s3_client:
            for bucket_name in [BucketNames.SOURCE, BucketNames.DESTINATION, BucketNames.MOCK_FIREHOSE]:
                for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                    s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                s3_client.delete_bucket(Bucket=bucket_name)

        if firehose_client:
            firehose_client.delete_delivery_stream(DeliveryStreamName=Firehose.STREAM_NAME)
