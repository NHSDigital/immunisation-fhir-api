"""This module contains the logging decorator for sending the appropriate logs to Cloudwatch and Firehose."""

import os
import time
from datetime import datetime
from functools import wraps

from common.log_decorator import generate_and_send_logs
from errors import InvalidHeaders, NoOperationPermissions

STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "immunisation-fhir-api-internal-dev-splunk-firehose")


def file_level_validation_logging_decorator(func):
    """
    Sends the appropriate logs to Cloudwatch and Firehose based on the result of the file_level_validation
    function call.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        incoming_message_body = kwargs.get("incoming_message_body") or args[0]
        base_log_data = {
            "function_name": f"record_processor_{func.__name__}",
            "date_time": str(datetime.now()),
            "file_key": incoming_message_body.get("filename"),
            "message_id": incoming_message_body.get("message_id"),
            "vaccine_type": incoming_message_body.get("vaccine_type"),
            "supplier": incoming_message_body.get("supplier"),
        }
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            additional_log_data = {
                "statusCode": 200,
                "message": "Successfully sent for record processing",
            }
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data)
            return result

        except (InvalidHeaders, NoOperationPermissions, Exception) as e:
            message = (
                str(e) if (isinstance(e, InvalidHeaders) or isinstance(e, NoOperationPermissions)) else "Server error"
            )
            status_code = 400 if isinstance(e, InvalidHeaders) else 403 if isinstance(e, NoOperationPermissions) else 500
            additional_log_data = {
                "statusCode": status_code,
                "message": message,
                "error": str(e),
            }
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data, is_error_log=True)
            raise

    return wrapper
