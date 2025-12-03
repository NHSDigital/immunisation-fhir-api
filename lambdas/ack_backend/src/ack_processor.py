"""Ack lambda handler"""

import json

# from audit_table import increment_record_counter
from common.batch.eof_utils import is_eof_message
from convert_message_to_ack_row import convert_message_to_ack_row
from logging_decorators import ack_lambda_handler_logging_decorator
from update_ack_file import complete_batch_file_process, update_ack_file


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
    supplier = None
    vaccine_type = None

    ack_data_rows = []
    file_processing_complete = False

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
            if is_eof_message(message):
                file_processing_complete = True
                break

            ack_data_rows.append(convert_message_to_ack_row(message, created_at_formatted_string))
            if message.get("diagnostics"):
                # TODO: unit tests will fail; we need to mock the audit table to get this to work.
                print("TODO: increment the record counter")
                # increment_record_counter(message_id)

    update_ack_file(file_key, created_at_formatted_string, ack_data_rows)

    if file_processing_complete:
        complete_batch_file_process(message_id, supplier, vaccine_type, created_at_formatted_string, file_key)

    return {
        "statusCode": 200,
        "body": json.dumps("Lambda function executed successfully!"),
    }
