"""Lambda Handler which streams batch file entries from Kinesis and forwards to the Imms FHIR API"""

import base64
import logging
import os
import time
from datetime import datetime

import simplejson as json

from batch.batch_filename_to_events_mapper import BatchFilenameToEventsMapper
from clients import sqs_client
from fhir_batch_controller import ImmunizationBatchController, make_batch_controller
from fhir_batch_repository import create_table
from models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    MessageNotSuccessfulError,
    RecordProcessorError,
    ResourceFoundError,
    ResourceNotFoundError,
)

logging.basicConfig(level="INFO")
logger = logging.getLogger()

QUEUE_URL = os.getenv("SQS_QUEUE_URL")


def create_diagnostics_dictionary(error: Exception) -> dict:
    """Returns a dictionary containing the error_type, statusCode, and error_message based on the type of the error"""

    # If error came from the record processor, then the diagnostics dictionary has already been completed
    if isinstance(error, RecordProcessorError):
        return error.diagnostics_dictionary

    error_type_to_status_code_map = {
        CustomValidationError: 400,
        IdentifierDuplicationError: 422,
        ResourceNotFoundError: 404,
        ResourceFoundError: 409,
        MessageNotSuccessfulError: 500,
    }

    return {
        "error_type": type(error).__name__,
        "statusCode": error_type_to_status_code_map.get(type(error), 500),
        "error_message": str(error),
    }


def forward_request_to_dynamo(
    message_body: any, table: any, is_present: bool, batch_controller: ImmunizationBatchController
):
    """Forwards the request to the Imms API (where possible) and updates the ack file with the outcome"""
    row_id = message_body.get("row_id")
    logger.info("FORWARDED MESSAGE: ID %s", row_id)
    return batch_controller.send_request_to_dynamo(message_body, table, is_present)


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""
    logger.info("Processing started")
    table = create_table()
    filename_to_events_mapper = BatchFilenameToEventsMapper()
    array_of_identifiers = []
    controller = make_batch_controller()

    for record in event["Records"]:
        try:
            operation_start_time = str(datetime.now())
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            incoming_message_body = json.loads(decoded_payload, use_decimal=True)

            file_key = incoming_message_body.get("file_key")
            created_at_formatted_string = incoming_message_body.get("created_at_formatted_string")
            base_outgoing_message_body = {
                "file_key": file_key,
                "row_id": incoming_message_body.get("row_id"),
                "created_at_formatted_string": created_at_formatted_string,
                "local_id": incoming_message_body.get("local_id"),
                "operation_requested": incoming_message_body.get("operation_requested"),
                "supplier": incoming_message_body.get("supplier"),
                "vaccine_type": incoming_message_body.get("vax_type"),
            }
            # TODO: Move section above here into own try-except block

            if incoming_diagnostics := incoming_message_body.get("diagnostics"):
                raise RecordProcessorError(incoming_diagnostics)

            if not (fhir_json := incoming_message_body.get("fhir_json")):
                raise MessageNotSuccessfulError("Server error - FHIR JSON not correctly sent to forwarder")

            # Check if the identifier is already present in the array
            identifier_already_present = False
            identifier_system = fhir_json["identifier"][0]["system"]
            identifier_value = fhir_json["identifier"][0]["value"]
            identifier = f"{identifier_system}#{identifier_value}"
            if identifier in array_of_identifiers:
                identifier_already_present = True
                delay_milliseconds = 30  # Delay time in milliseconds
                time.sleep(delay_milliseconds / 1000)  # TODO: What is the purpose of this delay?
            else:
                array_of_identifiers.append(identifier)

            imms_id = forward_request_to_dynamo(incoming_message_body, table, identifier_already_present, controller)
            filename_to_events_mapper.add_event(
                {
                    **base_outgoing_message_body,
                    "operation_start_time": operation_start_time,
                    "operation_end_time": str(datetime.now()),
                    "imms_id": imms_id,
                }
            )

        except Exception as error:  # pylint: disable = broad-exception-caught
            filename_to_events_mapper.add_event(
                {
                    **base_outgoing_message_body,
                    "operation_start_time": operation_start_time,
                    "operation_end_time": str(datetime.now()),
                    "diagnostics": create_diagnostics_dictionary(error),
                }
            )
            logger.error("Error processing message: %s", error)

    # Send to SQS
    for filename_key, events in filename_to_events_mapper.get_map().items():
        sqs_message_body = json.dumps(events)
        logger.info(f"total message length:{len(sqs_message_body)}")

        sqs_client.send_message(QueueUrl=QUEUE_URL, MessageBody=sqs_message_body, MessageGroupId=filename_key)


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
