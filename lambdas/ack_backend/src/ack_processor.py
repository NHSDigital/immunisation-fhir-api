"""Ack lambda handler"""

import json
from logging_decorators import ack_lambda_handler_logging_decorator
from update_ack_file import update_ack_file, complete_batch_file_process
from utils_for_ack_lambda import is_ack_processing_complete
from convert_message_to_ack_row import convert_message_to_ack_row


@ack_lambda_handler_logging_decorator
def lambda_handler(event, _):
    """
    Ack lambda handler.
    For each record: each message in the array of messages is converted to an ack row,
    then all of the ack rows for that array of messages are uploaded to the ack file in one go.
    """

    if not event.get("Records"):
        raise ValueError("Error in ack_processor_lambda_handler: No records found in the event")

    file_key = None
    created_at_formatted_string = None
    message_id = None

    ack_data_rows = []
    total_ack_rows_processed = 0

    for i, record in enumerate(event["Records"]):

        try:
            incoming_message_body = json.loads(record["body"])
        except Exception as body_json_error:
            raise ValueError("Could not load incoming message body") from body_json_error

        if i == 0:
            # The SQS FIFO MessageGroupId that this lambda consumes from is based on the source filename + created at
            # datetime. Therefore, can safely retrieve file metadata from the first record in the list
            file_key = incoming_message_body[0].get("file_key")
            message_id = (incoming_message_body[0].get("row_id", "")).split("^")[0]
            vaccine_type = incoming_message_body[0].get("vaccine_type")
            supplier = incoming_message_body[0].get("supplier")
            created_at_formatted_string = incoming_message_body[0].get("created_at_formatted_string")

        for message in incoming_message_body:
            ack_data_rows.append(convert_message_to_ack_row(message, created_at_formatted_string))

    update_ack_file(file_key, created_at_formatted_string, ack_data_rows)

    # Get the row count of the final processed record
    # Format of the row id is {batch_message_id}^{row_number}
    total_ack_rows_processed = int(incoming_message_body[-1].get("row_id", "").split("^")[1])

    if is_ack_processing_complete(message_id, total_ack_rows_processed):
        complete_batch_file_process(
            message_id, supplier, vaccine_type, created_at_formatted_string, file_key, total_ack_rows_processed
        )

    return {
        "statusCode": 200,
        "body": json.dumps("Lambda function executed successfully!"),
    }
