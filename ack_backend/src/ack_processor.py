"""Ack lambda handler"""

import json
from logging_decorators import ack_lambda_handler_logging_decorator
from update_ack_file import update_ack_file
from convert_message_to_ack_row import convert_message_to_ack_row


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
    message_id = None
    supplier_queue = None

    ack_data_rows = []

    for i, record in enumerate(event["Records"]):

        try:
            incoming_message_body = json.loads(record["body"])
        except Exception as body_json_error:
            raise ValueError("Could not load incoming message body") from body_json_error

        if i == 0:
            # IMPORTANT NOTE: An assumption is made here that the file_key and created_at_formatted_string are the same
            # for all messages in the event. The use of FIFO SQS queues ensures that this is the case, provided that
            # there is only one file processing at a time for each supplier queue (combination of supplier and vaccine
            # type).
            file_key = incoming_message_body[0].get("file_key")
            message_id = (incoming_message_body[0].get("row_id", "")).split("^")[0]
            vaccine_type = incoming_message_body[0].get("vaccine_type")
            supplier = incoming_message_body[0].get("supplier")
            supplier_queue = f"{supplier}_{vaccine_type}"
            created_at_formatted_string = incoming_message_body[0].get("created_at_formatted_string")

        for message in incoming_message_body:
            ack_data_rows.append(convert_message_to_ack_row(message, created_at_formatted_string))

    update_ack_file(file_key, message_id, supplier_queue, created_at_formatted_string, ack_data_rows)

    return {"statusCode": 200, "body": json.dumps("Lambda function executed successfully!")}
