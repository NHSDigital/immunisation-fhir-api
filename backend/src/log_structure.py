import logging
import time
from functools import wraps

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

def function_info(func):
    """This decorator prints the execution information for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[0] if args else {}
        headers = event.get('headers', {})
        correlation_id = headers.get('X-Correlation-ID', 'X-Correlation-ID not passed')
        request_id = headers.get('X-Request-ID', 'X-Request-ID not passed')
        actual_path = event.get('path', 'Unknown')
        resource_path = event.get('requestContext', {}).get('resourcePath', 'Unknown')
        logger.info(f"Starting {func.__name__} with X-Correlation-ID: {correlation_id} and X-Request-ID: {request_id}")

        try:
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()

            logger.info({
                "function_name": func.__name__,
                "time_taken": f"{round(end - start, 5)}s",
                "X-Correlation-ID": correlation_id,
                "X-Request-ID": request_id,
                "actual_path": actual_path,
                "resource_path": resource_path,
                "status": "completed successfully"
            })

            return result

        except Exception as e:
            logger.exception({
                "function_name": func.__name__,
                "time_taken": f"{round(time.time() - start, 5)}s",
                "X-Correlation-ID": correlation_id,
                "X-Request-ID": request_id,
                "actual_path": actual_path,
                "resource_path": resource_path,
                "error": str(e)
            })
            raise

    return wrapper