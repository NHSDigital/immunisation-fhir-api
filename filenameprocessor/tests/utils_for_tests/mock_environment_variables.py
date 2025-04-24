"""Module to hold mock environment variables for use in tests"""

REGION_NAME = "eu-west-2"

# NOTE: Moto mocking package uses a fixed account ID
MOCK_ACCOUNT_ID = "123456789012"


class BucketNames:
    """Class to hold bucket names for use in tests"""

    CONFIG = "immunisation-batch-internal-dev-data-configs"
    SOURCE = "immunisation-batch-internal-dev-data-sources"
    DESTINATION = "immunisation-batch-internal-dev-data-destinations"
    # Mock firehose bucket used for testing only (due to limitations of the moto testing package)
    MOCK_FIREHOSE = "mock-firehose-bucket"


class Firehose:
    """Class containing Firehose values for use in tests"""

    STREAM_NAME = "immunisation-fhir-api-internal-dev-splunk-firehose"


class Sqs:
    """Class to hold SQS values for use in tests"""

    ATTRIBUTES = {"FifoQueue": "true", "ContentBasedDeduplication": "true"}
    QUEUE_NAME = "imms-batch-internal-dev-metadata-queue.fifo"
    TEST_QUEUE_URL = (
        f"https://sqs.{REGION_NAME}.amazonaws.com/{MOCK_ACCOUNT_ID}/{QUEUE_NAME}"
    )


# Dictionary for mocking the os.environ dict
# NOTE: FILE_NAME_GSI and CONFIG_BUCKET_NAME environment variables are set in the terraform,
# but not used in the src code and so are not set here.
MOCK_ENVIRONMENT_DICT = {
    "SOURCE_BUCKET_NAME": BucketNames.SOURCE,
    "ACK_BUCKET_NAME": BucketNames.DESTINATION,
    "QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/imms-batch-internal-dev-metadata-queue.fifo",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "SPLUNK_FIREHOSE_NAME": Firehose.STREAM_NAME,
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
    "FILE_NAME_PROC_LAMBDA_NAME": "imms-batch-internal-dev-filenameproc_lambda",
}
