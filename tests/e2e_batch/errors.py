class AckFileNotFoundError(Exception):
    """Raised when the acknowledgment file is not found."""


class DynamoDBMismatchError(Exception):
    """Raised when DynamoDB primary key doesn't match the ACK file IMMS_ID."""
