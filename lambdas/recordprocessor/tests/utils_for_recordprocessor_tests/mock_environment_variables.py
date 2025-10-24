"""Mock environment variables for use in recordprocessor tests"""

REGION_NAME = "eu-west-2"


class BucketNames:
    """Class containing bucket names for use in tests"""

    SOURCE = "immunisation-batch-internal-dev-data-sources"
    DESTINATION = "immunisation-batch-internal-dev-data-destinations"
    MOCK_FIREHOSE = "mock-firehose-bucket"


class Kinesis:
    """Class containing Kinesis values for use in tests"""

    STREAM_NAME = "imms-batch-internal-dev-processingdata-stream"


class Firehose:
    """Class containing Firehose values for use in tests"""

    STREAM_NAME = "immunisation-fhir-api-internal-dev-splunk-firehose"


class Sqs:
    """Class to hold SQS values for use in tests"""

    ATTRIBUTES = {"FifoQueue": "true", "ContentBasedDeduplication": "true"}
    QUEUE_NAME = "imms-batch-internal-dev-metadata-queue.fifo"
    TEST_QUEUE_URL = f"https://sqs.{REGION_NAME}.amazonaws.com/999999999/{QUEUE_NAME}"


MOCK_ENVIRONMENT_DICT = {
    "ENVIRONMENT": "internal-dev",
    "LOCAL_ACCOUNT_ID": "123456789012",
    "SOURCE_BUCKET_NAME": BucketNames.SOURCE,
    "ACK_BUCKET_NAME": BucketNames.DESTINATION,
    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
    "KINESIS_STREAM_NAME": Kinesis.STREAM_NAME,
    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:{REGION_NAME}:123456789012:stream/{Kinesis.STREAM_NAME}",
    "FIREHOSE_STREAM_NAME": Firehose.STREAM_NAME,
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
}
