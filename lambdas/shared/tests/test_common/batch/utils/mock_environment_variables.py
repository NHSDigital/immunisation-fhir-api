"""Mock environment variables for use in recordprocessor tests"""

REGION_NAME = "eu-west-2"


class BucketNames:
    """Class containing bucket names for use in tests"""

    SOURCE = "immunisation-batch-internal-dev-data-sources"
    DESTINATION = "immunisation-batch-internal-dev-data-destinations"


MOCK_ENVIRONMENT_DICT = {
    "ENVIRONMENT": "internal-dev",
    "LOCAL_ACCOUNT_ID": "123456789012",
    "SOURCE_BUCKET_NAME": BucketNames.SOURCE,
    "ACK_BUCKET_NAME": BucketNames.DESTINATION,
    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
}
