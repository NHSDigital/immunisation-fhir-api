"""
Centralised observability for MNS publisher Lambda.

log_uncaught_exceptions=True ensures unexpected exceptions are captured as
structured JSON logs at the Lambda boundary.
"""

from __future__ import annotations

import os

from aws_lambda_powertools import Logger

_SERVICE_NAME = "mns-immunisation-publisher."

logger: Logger = Logger(
    service=_SERVICE_NAME,
    level=os.environ.get("LOG_LEVEL", "INFO"),
    log_uncaught_exceptions=True,
    location=False,
)
