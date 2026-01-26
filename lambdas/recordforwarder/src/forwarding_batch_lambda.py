"""Lambda Handler which streams batch file entries from Kinesis and forwards to the Imms FHIR API"""

import base64
import logging
import os
from datetime import datetime

import simplejson as json
from mypy_boto3_dynamodb import DynamoDBServiceResource

from batch.batch_filename_to_events_mapper import BatchFilenameToEventsMapper
from common.batch.eof_utils import is_eof_message
from common.clients import get_sqs_client
from common.models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    ResourceFoundError,
    ResourceNotFoundError,
)
from controller.fhir_batch_controller import (
    ImmunizationBatchController,
    make_batch_controller,
)
from models.errors import (
    MessageNotSuccessfulError,
    RecordProcessorError,
)
from repository.fhir_batch_repository import create_table

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
    message_body: dict,
    table: DynamoDBServiceResource,
    last_imms_pk: str,
    batch_controller: ImmunizationBatchController,
):
    """Forwards the request to the Imms API (where possible) and updates the ack file with the outcome"""
    row_id = message_body.get("row_id")
    logger.info("FORWARDED MESSAGE: ID %s", row_id)
    return batch_controller.send_request_to_dynamo(message_body, table, last_imms_pk)


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""
    logger.info("Processing started")
    table = create_table()
    filename_to_events_mapper = BatchFilenameToEventsMapper()
    list_of_identifiers = {}
    controller = make_batch_controller()

    for record in event["Records"]:
        operation_start_time = str(datetime.now())
        kinesis_payload = record["kinesis"]["data"]
        decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
        incoming_message_body = json.loads(decoded_payload, use_decimal=True)
        file_key = incoming_message_body.get("file_key")
        local_id = incoming_message_body.get("local_id")

        if is_eof_message(incoming_message_body):
            logger.info("Received EOF message for file key: %s", file_key)
            filename_to_events_mapper.add_event(incoming_message_body)
            continue

        base_outgoing_message_body = {
            "file_key": incoming_message_body.get("file_key"),
            "row_id": incoming_message_body.get("row_id"),
            "created_at_formatted_string": incoming_message_body.get("created_at_formatted_string"),
            "local_id": incoming_message_body.get("local_id"),
            "operation_requested": incoming_message_body.get("operation_requested"),
            "supplier": incoming_message_body.get("supplier"),
            "vaccine_type": incoming_message_body.get("vax_type"),
        }
        logger.info("Received message for file %s with local id: %s", file_key, local_id)

        try:
            if incoming_diagnostics := incoming_message_body.get("diagnostics"):
                raise RecordProcessorError(incoming_diagnostics)

            if not (fhir_json := incoming_message_body.get("fhir_json")):
                raise MessageNotSuccessfulError("Server error - FHIR JSON not correctly sent to forwarder")

            # Check if the identifier is already present in the array
            identifier_system = fhir_json["identifier"][0]["system"]
            identifier_value = fhir_json["identifier"][0]["value"]
            identifier = f"{identifier_system}#{identifier_value}"
            last_imms_pk = list_of_identifiers.get(identifier)

            imms_pk = forward_request_to_dynamo(incoming_message_body, table, last_imms_pk, controller)
            list_of_identifiers[identifier] = imms_pk
            logger.info("Successfully processed message. Local id: %s, PK: %s", local_id, imms_pk)

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

        get_sqs_client().send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=sqs_message_body,
            MessageGroupId=filename_key,
        )


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
