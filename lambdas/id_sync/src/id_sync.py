from common.clients import logger
from common.clients import STREAM_NAME
from common.log_decorator import logging_decorator
from common.aws_lambda_event import AwsLambdaEvent
from exceptions.id_sync_exception import IdSyncException
from record_processor import process_record
'''
Lambda function handler for processing SQS events.Lambda for ID Sync. Fired by SQS
'''


@logging_decorator(prefix="id_sync", stream_name=STREAM_NAME)
def handler(event_data, _):

    try:
        logger.info("id_sync handler invoked")
        event = AwsLambdaEvent(event_data)
        record_count = len(event.records)
        if record_count > 0:
            logger.info("id_sync processing event with %d records", record_count)
            error_count = 0
            nhs_numbers = []
            for record in event.records:
                record_result = process_record(record)
                nhs_numbers.append(record_result["nhs_number"])
                if record_result["status"] == "error":
                    error_count += 1
            if error_count > 0:
                raise IdSyncException(message=f"Processed {record_count} records with {error_count} errors",
                                      nhs_numbers=nhs_numbers)

            else:
                response = {"status": "success",
                            "message": f"Successfully processed {record_count} records",
                            "nhs_numbers": nhs_numbers}
        else:
            response = {"status": "success", "message": "No records found in event"}
        logger.info("id_sync handler completed: %s", response)
        return response
    except IdSyncException as e:
        logger.exception(f"id_sync error: {e.message}")
        raise e
    except Exception as e:
        msg = "Error processing id_sync event"
        logger.exception(msg)
        raise IdSyncException(message=msg, exception=e)
