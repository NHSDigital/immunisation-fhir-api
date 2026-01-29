"""Constants for ack lambda"""

COMPLETED_ACK_DIR = "forwardedFile"
BATCH_FILE_PROCESSING_DIR = "processing"
BATCH_FILE_ARCHIVE_DIR = "archive"
LAMBDA_FUNCTION_NAME_PREFIX = "ack_processor"
DEFAULT_STREAM_NAME = "immunisation-fhir-api-internal-dev-splunk-firehose"


ACK_HEADERS = [
    "MESSAGE_HEADER_ID",
    "HEADER_RESPONSE_CODE",
    "ISSUE_SEVERITY",
    "ISSUE_CODE",
    "ISSUE_DETAILS_CODE",
    "RESPONSE_TYPE",
    "RESPONSE_CODE",
    "RESPONSE_DISPLAY",
    "RECEIVED_TIME",
    "MAILBOX_FROM",
    "LOCAL_ID",
    "IMMS_ID",
    "OPERATION_OUTCOME",
    "MESSAGE_DELIVERY",
]
