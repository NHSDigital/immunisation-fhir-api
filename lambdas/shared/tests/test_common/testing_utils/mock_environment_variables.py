"""Mock environment variables for use in tests"""


class BucketNames:
    """Class containing bucket names for use in tests"""

    SOURCE = "immunisation-batch-internal-dev-data-sources"
    DESTINATION = "immunisation-batch-internal-dev-data-destinations"
    MOCK_FIREHOSE = "mock-firehose-bucket"


MOCK_ENVIRONMENT_DICT = {
    "ACK_BUCKET_NAME": BucketNames.DESTINATION,
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
}
