"""Decorators for logging and sending logs to Firehose"""

import os
import time
from datetime import datetime
from functools import wraps
from common.log_decorator import generate_and_send_logs

PREFIX = "ack_processor"
STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME", "immunisation-fhir-api-internal-dev-splunk-firehose")


def convert_message_to_ack_row_logging_decorator(func):
    """This decorator logs the information on the conversion of a single message to an ack data row"""

    @wraps(func)
    def wrapper(message, created_at_formatted_string):
        base_log_data = {"function_name": f"{PREFIX}_{func.__name__}", "date_time": str(datetime.now())}
        start_time = time.time()

        try:
            result = func(message, created_at_formatted_string)

            file_key = message.get("file_key", "file_key_missing")
            message_id = message.get("row_id", "unknown")
            diagnostics = message.get("diagnostics")

            additional_log_data = {
                "file_key": file_key,
                "message_id": message_id,
                "operation_start_time": message.get("operation_start_time", "unknown"),
                "operation_end_time": message.get("operation_end_time", "unknown"),
                "vaccine_type": message.get("vaccine_type", "unknown"),
                "supplier": message.get("supplier", "unknown"),
                "local_id": message.get("local_id", "unknown"),
                "operation_requested": message.get("operation_requested", "unknown"),
                **process_diagnostics(diagnostics, file_key, message_id),
            }
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data, use_ms_precision=True)

            return result

        except Exception as error:
            additional_log_data = {"status": "fail", "statusCode": 500, "diagnostics": str(error)}
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data, use_ms_precision=True,
                                   is_error_log=True)
            raise

    return wrapper


def upload_ack_file_logging_decorator(func):
    """This decorator logs when record processing is complete."""

    @wraps(func)
    def wrapper(*args, **kwargs):

        base_log_data = {"function_name": f"{PREFIX}_{func.__name__}", "date_time": str(datetime.now())}
        start_time = time.time()

        # NB this doesn't require a try-catch block as the wrapped function never throws an exception
        result = func(*args, **kwargs)
        if result is not None:
            message_for_logs = "Record processing complete"
            base_log_data.update(result)
            additional_log_data = {"status": "success", "statusCode": 200, "message": message_for_logs}
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data)
        return result

    return wrapper


def ack_lambda_handler_logging_decorator(func):
    """This decorator logs the execution info for the ack lambda handler."""

    @wraps(func)
    def wrapper(event, context, *args, **kwargs):

        base_log_data = {"function_name": f"{PREFIX}_{func.__name__}", "date_time": str(datetime.now())}
        start_time = time.time()

        try:
            result = func(event, context, *args, **kwargs)
            message_for_logs = "Lambda function executed successfully!"
            additional_log_data = {"status": "success", "statusCode": 200, "message": message_for_logs}
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data)
            return result

        except Exception as error:
            additional_log_data = {"status": "fail", "statusCode": 500, "diagnostics": str(error)}
            generate_and_send_logs(STREAM_NAME, start_time, base_log_data, additional_log_data, is_error_log=True)
            raise

    return wrapper


def process_diagnostics(diagnostics, file_key, message_id):
    """Returns a dictionary containing the status, statusCode and diagnostics"""
    if diagnostics is not None:
        return {
            "status": "fail",
            "statusCode": diagnostics.get("statusCode") if isinstance(diagnostics, dict) else 500,
            "diagnostics": (
                diagnostics.get("error_message")
                if isinstance(diagnostics, dict)
                else "Unable to determine diagnostics issue"
            ),
        }

    if file_key == "file_key_missing" or message_id == "unknown":
        diagnostics = "An unhandled error occurred during batch processing"
        return {"status": "fail", "statusCode": 500, "diagnostics": diagnostics}

    return {"status": "success", "statusCode": 200, "diagnostics": "Operation completed successfully"}
