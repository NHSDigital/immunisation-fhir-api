"""Module containing mock environment variables for use in ack backend tests"""

REGION_NAME = "eu-west-2"


class BucketNames:
    """Bucket Names for testing"""

    SOURCE = "immunisation-batch-internal-dev-data-sources"
    DESTINATION = "immunisation-batch-internal-dev-data-destinations"
    MOCK_FIREHOSE = "mock-firehose-bucket"


class Firehose:
    """Class containing Firehose values for use in tests"""

    STREAM_NAME = "immunisation-fhir-api-internal-dev-splunk-firehose"


MOCK_ENVIRONMENT_DICT = {
    "ACK_BUCKET_NAME": BucketNames.DESTINATION,
    "FIREHOSE_STREAM_NAME": Firehose.STREAM_NAME,
    "AUDIT_TABLE_NAME": "immunisation-batch-internal-dev-audit-table",
    "ENVIRONMENT": "internal-dev",
}
