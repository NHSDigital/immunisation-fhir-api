import json

from aws_lambda_typing import context, events
from batch_file_created_event import BatchFileCreatedEvent
from batch_processor_filter_service import BatchProcessorFilterService
from exception_decorator import exception_decorator
from exceptions import InvalidBatchSizeError

service = BatchProcessorFilterService()


@exception_decorator
def lambda_handler(event: events.SQSEvent, _: context.Context):
    event_records = event.get("Records", [])

    # Terraform is configured so the Lambda will get a max batch size of 1. We are using SQS FIFO with the message group
    # id set to {supplier}_{vaccine_type} so it makes sense to only process batches of 1 at a time.
    # Lambda will scale out to handle multiple message groups in parallel so this will not block other groups:
    # https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/fifo-queue-lambda-behavior.html
    if len(event_records) != 1:
        raise InvalidBatchSizeError(f"Received {len(event_records)} records, expected 1")

    batch_file_created_event: BatchFileCreatedEvent = json.loads(event_records[0].get("body"))
    service.apply_filter(batch_file_created_event)
