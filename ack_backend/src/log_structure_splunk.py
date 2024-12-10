import logging
import json
import time
from datetime import datetime
from functools import wraps
from log_firehose_splunk import FirehoseLogger
from constants import extract_file_key_elements, get_status_code_for_diagnostics

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

firehose_logger = FirehoseLogger()


def ack_function_info(func):
    """This decorator logs the execution info for the decorated function and sends it to Splunk."""

    @wraps(func)
    def wrapper(event, context, *args, **kwargs):
        log_data = {
            "function_name": f"ack_processor_{func.__name__}",
            "date_time": str(datetime.now()),
            "time_taken": None,
            "status": None,
            "statusCode": None,
            "diagnostics": None,
        }

        start_time = time.time()
        firehose_log = dict()

        try:
            if event and "Records" in event:
                for record in event["Records"]:
                    try:
                        body_json = record["body"]
                        incoming_message_body = json.loads(body_json)
                        if not isinstance(incoming_message_body, list):
                            incoming_message_body = [incoming_message_body]

                        for item in incoming_message_body:
                            file_key = item.get("file_key", "file_key_missing")
                            log_data["file_key"] = file_key

                            if file_key != "file_key_missing":
                                try:
                                    file_key_elements = extract_file_key_elements(file_key)
                                    log_data["vaccine_type"] = file_key_elements.get("vaccine_type", "unknown")
                                    log_data["supplier"] = file_key_elements.get("supplier", "unknown")
                                except Exception as e:
                                    logger.warning(f"Error parsing file key: {file_key}. Error: {e}")

                            log_data["message_id"] = item.get("row_id", "unknown")
                            message_id = log_data["message_id"]
                            log_data["local_id"] = item.get("local_id", "unknown")
                            log_data["operation_requested"] = item.get("action_flag", "unknown")
                            diagnostics = item.get("diagnostics")
                            diagnostics_result = process_diagnostics(diagnostics, file_key, message_id)
                            log_data.update(diagnostics_result)
                            log_data["time_taken"] = f"{round(time.time() - start_time, 5)}s"
                            firehose_log["event"] = log_data
                            try:
                                logger.info(f"Function executed successfully: {json.dumps(log_data)}")
                                firehose_logger.ack_send_log(firehose_log)
                            except Exception:
                                logger.warning("Issue with logging")

                    except Exception as record_error:
                        logger.error(f"Error processing record: {record}. Error: {record_error}")

            result = func(event, context, *args, **kwargs)
            return result

        except Exception as e:
            end_time = time.time()
            log_data["time_taken"] = f"{round(end_time - start_time, 5)}s"
            log_data["status"] = "fail"
            log_data["statusCode"] = 500
            log_data["diagnostics"] = f"Error in ack_processor_{func.__name__}: {str(e)}"
            try:
                logger.exception(f"Critical error in function: logging for {func.__name__}")
                firehose_log["event"] = log_data
                firehose_logger.ack_send_log(firehose_log)
            except Exception:
                logger.warning("Issue with logging ")

            raise

    return wrapper


def process_diagnostics(diagnostics, file_key, message_id):
    """selects the status code and diagnostics for incoming messages"""
    if diagnostics is not None:
        return {
            "status": "fail",
            "statusCode": get_status_code_for_diagnostics(diagnostics),
            "diagnostics": diagnostics,
        }
    if diagnostics is None and file_key != "file_key_missing" and message_id != "unknown":
        return {"status": "success", "statusCode": 200, "diagnostics": "Operation completed successfully"}

    return {"status": "fail", "statusCode": 500, "diagnostics": "An unhandled error happened during batch processing"}
