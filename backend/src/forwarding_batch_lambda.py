"""Functions for forwarding each row to the Imms API"""

import os
import simplejson as json
import base64
import time
import logging
from fhir_batch_repository import create_table
from fhir_batch_controller import ImmunizationBatchController, make_batch_controller
from clients import sqs_client


logging.basicConfig(level="INFO")
logger = logging.getLogger()

QUEUE_URL = os.getenv("SQS_QUEUE_URL")


def forward_request_to_dynamo(message_body: any, table: any, is_present: bool, batchcontroller: ImmunizationBatchController):
    """Forwards the request to the Imms API (where possible) and updates the ack file with the outcome"""
    row_id = message_body.get("row_id")
    logger.info("FORWARDED MESSAGE: ID %s", row_id)
    return batchcontroller.send_request_to_dynamo(message_body, table, is_present)


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""
    logger.info("Processing started")
    table = create_table()
    array_of_messages = []
    array_of_identifiers = []
    controller = make_batch_controller()
    for record in event["Records"]:
        try:
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload, use_decimal=True)
            is_present = False
            if fhir_json := message_body.get("fhir_json"):
                system_id = fhir_json["identifier"][0]["system"]
                system_value = fhir_json["identifier"][0]["value"]
                identifier = f"{system_id}#{system_value}"
                if identifier in array_of_identifiers:
                    is_present = True
                    delay_milliseconds = 30 # Delay time in milliseconds 
                    time.sleep(delay_milliseconds / 1000)
                else:
                    array_of_identifiers.append(identifier)
                
            file_key = message_body.get("file_key")
            created_at_formatted_string = message_body.get("created_at_formatted_string")
            message_group_id = f"{file_key}_{created_at_formatted_string}"
            response = {}
            response["imms_id"] = forward_request_to_dynamo(
                message_body, table, is_present, controller
            )
            response["file_key"] = file_key
            response["row_id"] = message_body.get("row_id")
            response["created_at_formatted_string"] = created_at_formatted_string
            response["local_id"] = message_body.get("local_id")
            response["action_flag"] = message_body.get("operation_requested")
            array_of_messages.append(response)
        except Exception as error:
            error_message_body = {
                "diagnostics": str(error),
                "file_key": message_body.get("file_key"),
                "row_id": message_body.get("row_id"),
                "created_at_formatted_string": message_body.get("created_at_formatted_string"),
                "local_id": message_body.get("local_id"),
                "action_flag": message_body.get("operation_requested"),
            }
            array_of_messages.append(error_message_body)
            logger.error("Error processing message: %s", error)
    sqs_message_body = json.dumps(array_of_messages)
    message_len = len(sqs_message_body)
    logger.info(f"total message length:{message_len}")
    if message_len < 256 * 1024 :
        sqs_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=sqs_message_body,
            MessageGroupId=message_group_id,
        )
        # array_of_messages = []
    else:
        logger.info("Message size exceeds 256 KB limit.Sending to sqs failed")


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
