"""Decorators for logging and sending logs to Firehose"""

import os
import json
import time
from datetime import datetime
from functools import wraps
from clients import firehose_client, logger


STREAM_NAME = os.getenv(
    "SPLUNK_FIREHOSE_NAME", "immunisation-fhir-api-internal-dev-splunk-firehose"
)


def send_log_to_firehose(log_data: dict) -> None:
    """Sends the log_message to Firehose"""
    try:
        record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        firehose_client.put_record(DeliveryStreamName=STREAM_NAME, Record=record)
        logger.info("Log sent to Firehose")
    except Exception as error:  # pylint:disable = broad-exception-caught
        logger.exception("Error sending log to Firehose: %s", error)


def generate_and_send_logs(
    start_time,
    base_log_data: dict,
    additional_log_data: dict,
    is_error_log: bool = False,
) -> None:
    """Generates log data which includes the base_log_data, additional_log_data, and time taken (calculated using the
    current time and given start_time) and sends them to Cloudwatch and Firehose."""
    log_data = {
        **base_log_data,
        "time_taken": f"{round(time.time() - start_time, 5)}s",
        **additional_log_data,
    }
    log_function = logger.error if is_error_log else logger.info
    log_function(json.dumps(log_data))
    send_log_to_firehose(log_data)


def convert_messsage_to_ack_row_logging_decorator(func):
    """This decorator logs the information on the conversion of a single message to an ack data row"""

    @wraps(func)
    def wrapper(message, created_at_formatted_string):

        base_log_data = {
            "function_name": f"ack_processor_{func.__name__}",
            "date_time": str(datetime.now()),
        }
        start_time = time.time()

        try:
            result = func(message, created_at_formatted_string)

            file_key = message.get("file_key", "file_key_missing")
            message_id = message.get("row_id", "unknown")
            diagnostics = message.get("diagnostics")

            additional_log_data = {
                "file_key": file_key,
                "message_id": message_id,
                "vaccine_type": message.get("vaccine_type", "unknown"),
                "supplier": message.get("supplier", "unknown"),
                "local_id": message.get("local_id", "unknown"),
                "operation_requested": message.get("operation_requested", "unknown"),
                **process_diagnostics(diagnostics, file_key, message_id),
            }
            generate_and_send_logs(start_time, base_log_data, additional_log_data)

            return result

        except Exception as error:
            additional_log_data = {
                "status": "fail",
                "statusCode": 500,
                "diagnostics": str(error),
            }
            generate_and_send_logs(
                start_time, base_log_data, additional_log_data, is_error_log=True
            )
            raise

    return wrapper


def ack_lambda_handler_logging_decorator(func):
    """This decorator logs the execution info for the ack lambda handler."""

    @wraps(func)
    def wrapper(event, context, *args, **kwargs):

        base_log_data = {
            "function_name": f"ack_processor_{func.__name__}",
            "date_time": str(datetime.now()),
        }
        start_time = time.time()

        try:
            result = func(event, context, *args, **kwargs)
            message_for_logs = "Lambda function executed successfully!"
            additional_log_data = {
                "status": "success",
                "statusCode": 200,
                "message": message_for_logs,
            }
            generate_and_send_logs(start_time, base_log_data, additional_log_data)
            return result

        except Exception as error:
            additional_log_data = {
                "status": "fail",
                "statusCode": 500,
                "diagnostics": str(error),
            }
            generate_and_send_logs(
                start_time, base_log_data, additional_log_data, is_error_log=True
            )
            raise

    return wrapper


def process_diagnostics(diagnostics, file_key, message_id):
    """Returns a dictionary containing the status, statusCode and diagnostics"""
    if diagnostics is not None:
        return {
            "status": "fail",
            "statusCode": (
                diagnostics.get("statusCode") if isinstance(diagnostics, dict) else 500
            ),
            "diagnostics": (
                diagnostics.get("error_message")
                if isinstance(diagnostics, dict)
                else "Unable to determine diagnostics issue"
            ),
        }

    if file_key == "file_key_missing" or message_id == "unknown":
        diagnostics = "An unhandled error occurred during batch processing"
        return {"status": "fail", "statusCode": 500, "diagnostics": diagnostics}

    return {
        "status": "success",
        "statusCode": 200,
        "diagnostics": "Operation completed successfully",
    }
