"""Ack lambda handler"""

import json
from utils_for_ack_lambda import get_environment
from typing import Union
from logging_decorators import ack_lambda_handler_logging_decorator, convert_messsage_to_ack_row_logging_decorator
from update_ack_file import update_ack_file, create_ack_data
from clients import s3_client


ENVIRONMENT = get_environment()
SOURCE_BUCKET_NAME = f"immunisation-batch-{ENVIRONMENT}-data-sources"

@convert_messsage_to_ack_row_logging_decorator
def convert_message_to_ack_row(message, created_at_formatted_string):
    """
    Takes a single message and returns the ack data row for that message.
    A value error is raised if the file_key or created_at_formatted_string for the message do not match the
    expected values.
    """
    error_message_for_ack_file: Union[None, str]
    if (diagnostics := message.get("diagnostics")) is None:
        error_message_for_ack_file = None
    elif isinstance(diagnostics, dict):
        status_code = diagnostics.get("statusCode")
        if status_code is None or status_code == 500:
            error_message_for_ack_file = "An unhandled error occurred during batch processing"
        else:
            error_message_for_ack_file = diagnostics.get("error_message", "Unable to determine diagnostics issue")
    else:
        error_message_for_ack_file = "Unable to determine diagnostics issue"

    return create_ack_data(
        created_at_formatted_string=created_at_formatted_string,
        local_id=message.get("local_id"),
        row_id=message.get("row_id"),
        successful_api_response=diagnostics is None,  # Response is successful if and only if there are no diagnostics
        diagnostics=error_message_for_ack_file,
        imms_id=message.get("imms_id"),
    )


@ack_lambda_handler_logging_decorator
def lambda_handler(event, context):
    """
    Ack lambda handler.
    For each record: each message in the array of messages is converted to an ack row,
    then all of the ack rows for that array of messages are uploaded to the ack file in one go.
    """

    if not event.get("Records"):
        raise ValueError("Error in ack_processor_lambda_handler: No records found in the event")

    file_key = None
    created_at_formatted_string = None

    array_of_rows = []
    
    for i, record in enumerate(event["Records"]):

        try:
            incoming_message_body = json.loads(record["body"])
        except Exception as body_json_error:
            raise ValueError("Could not load incoming message body") from body_json_error

        if i == 0:
            # IMPORTANT NOTE: An assumption is made here that the file_key and created_at_formatted_string are the same
            # for all messages in the event. The use of FIFO SQS queues ensures that this is the case.
            file_key = incoming_message_body[0].get("file_key")
            created_at_formatted_string = incoming_message_body[0].get("created_at_formatted_string")

        for message in incoming_message_body:
            array_of_rows.append(convert_message_to_ack_row(message, created_at_formatted_string))
    row_count = get_row_count_stream(SOURCE_BUCKET_NAME, f"processing/{file_key}")
    update_ack_file(file_key, created_at_formatted_string=created_at_formatted_string, ack_data_rows=array_of_rows, row_count=row_count)
    return {"statusCode": 200, "body": json.dumps("Lambda function executed successfully!")}


def get_row_count_stream(bucket_name, key):
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    count = sum(1 for line in response['Body'].iter_lines() if line.strip())
 
    return count