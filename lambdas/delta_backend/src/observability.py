"""
Centralised observability for Delta Lambda.

log_uncaught_exceptions=True means any unhandled exception at handler
boundary is logged as structured JSON before Lambda runtime kills the
invocation, complementing the existing DLQ routing.

Log level is set via env var at the Lambda function level when needed.

correlation_id_path is omitted as DynamoDB Streams
events does not have a correlation ID. eventID is used
and is added in process_record().
"""

from __future__ import annotations

import os

from aws_lambda_powertools import Logger

# Service name used in all structured log entries.
# Keep consistent with the Lambda function name convention in delta.tf.
_SERVICE_NAME = "delta"

logger: Logger = Logger(
    service=_SERVICE_NAME,
    # Respect LOG_LEVEL env var; default INFO for production safety.
    level=os.environ.get("LOG_LEVEL", "INFO"),
    # Serialise uncaught exceptions as structured JSON.
    log_uncaught_exceptions=True,
    location=False,
)
