import json
import time
from datetime import datetime
from functools import wraps

from common.clients import STREAM_NAME, logger
from common.log_firehose import send_log_to_firehose
from common.models.utils.validation_utils import get_vaccine_type


def _log_data_from_body(event) -> dict:
    log_data = {}
    if event.get("body") is None:
        return log_data
    try:
        imms = json.loads(event["body"])
    except json.decoder.JSONDecodeError:
        return log_data
    try:
        vaccine_type = get_vaccine_type(imms)
        log_data["vaccine_type"] = vaccine_type
    except Exception:
        pass
    try:
        local_id = imms["identifier"][0]["value"] + "^" + imms["identifier"][0]["system"]
        log_data["local_id"] = local_id
    except Exception:
        pass
    return log_data


def _get_operation_outcome(result) -> dict:
    operation_outcome = {}
    status = "500"
    status_code = "Exception"
    diagnostics = str()
    record = str()
    if isinstance(result, dict):
        status = str(result["statusCode"])
        status_code = "Completed successfully"
        if result.get("headers"):
            result_headers = result["headers"]
            if result_headers.get("Location"):
                record = result_headers["Location"]
        if result.get("body"):
            ops_outcome = json.loads(result["body"])
            if ops_outcome.get("issue"):
                outcome_body = ops_outcome["issue"][0]
                status_code = outcome_body["code"]
                diagnostics = outcome_body["diagnostics"]
    operation_outcome["status"] = status
    operation_outcome["status_code"] = status_code
    if len(diagnostics) > 1:
        operation_outcome["diagnostics"] = diagnostics
    if len(record) > 1:
        operation_outcome["record"] = record
    return operation_outcome


def function_info(func):
    """This decorator prints the execution information for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[0] if args else {}
        headers = event.get("headers", {})
        correlation_id = headers.get("X-Correlation-ID", "X-Correlation-ID not passed")
        request_id = headers.get("X-Request-ID", "X-Request-ID not passed")
        supplier_system = headers.get("SupplierSystem", "SupplierSystem not passed")
        actual_path = event.get("path", "Unknown")
        resource_path = event.get("requestContext", {}).get("resourcePath", "Unknown")
        logger.info(f"Starting {func.__name__} with X-Correlation-ID: {correlation_id} and X-Request-ID: {request_id}")
        log_data = {
            "function_name": func.__name__,
            "date_time": str(datetime.now()),
            "X-Correlation-ID": correlation_id,
            "X-Request-ID": request_id,
            "supplier": supplier_system,
            "actual_path": actual_path,
            "resource_path": resource_path,
        }
        start = time.time()
        try:
            result = func(*args, **kwargs)
            end = time.time()
            log_data["time_taken"] = f"{round(end - start, 5)}s"
            log_data.update(_log_data_from_body(event))
            operation_outcome = _get_operation_outcome(result)

            log_data["operation_outcome"] = operation_outcome
            logger.info(json.dumps(log_data))
            send_log_to_firehose(STREAM_NAME, log_data)
            return result

        except Exception as e:
            log_data["error"] = str(e)
            end = time.time()
            log_data["time_taken"] = f"{round(end - start, 5)}s"
            log_data.update(_log_data_from_body(event))
            logger.exception(json.dumps(log_data))
            send_log_to_firehose(STREAM_NAME, log_data)
            raise

    return wrapper
