"""This module contains the logging decorator for sending the appropriate logs to Cloudwatch and Firehose."""

import json
import os
import time
from datetime import datetime
from functools import wraps
from clients import firehose_client, logger
from errors import NoOperationPermissions, InvalidHeaders

STREAM_NAME = os.getenv(
    "SPLUNK_FIREHOSE_NAME", "immunisation-fhir-api-internal-dev-splunk-firehose"
)


def send_log_to_firehose(log_data: dict) -> None:
    """Sends the log_message to Firehose"""
    try:
        record = {"Data": json.dumps({"event": log_data}).encode("utf-8")}
        response = firehose_client.put_record(
            DeliveryStreamName=STREAM_NAME, Record=record
        )
        logger.info(
            "Log sent to Firehose: %s", response
        )  # TODO: Should we be logging full response?
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
            generate_and_send_logs(
                start_time, base_log_data, additional_log_data=additional_log_data
            )
            return result

        except (InvalidHeaders, NoOperationPermissions, Exception) as e:
            message = (
                str(e)
                if (
                    isinstance(e, InvalidHeaders)
                    or isinstance(e, NoOperationPermissions)
                )
                else "Server error"
            )
            status_code = (
                400
                if isinstance(e, InvalidHeaders)
                else 403 if isinstance(e, NoOperationPermissions) else 500
            )
            additional_log_data = {
                "statusCode": status_code,
                "message": message,
                "error": str(e),
            }
            generate_and_send_logs(
                start_time, base_log_data, additional_log_data, is_error_log=True
            )
            raise

    return wrapper
