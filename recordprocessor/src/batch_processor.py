"""Application to convert rows from batch files to FHIR and forward to Kinesis for further downstream processing"""

import json
import os
import time
from process_row import process_row
from mappings import map_target_disease
from send_to_kinesis import send_to_kinesis
from clients import logger
from file_level_validation import file_level_validation
from logging_decorator import ingestion_logging_decorator
from errors import NoOperationPermissions, InvalidHeaders


@ingestion_logging_decorator
def ingestion_progress(finished: bool, message_body: dict, row_count: int = 0, start_time: float = 0.0) -> str:
    return("Ingestion finished" if finished else "Ingestion started")


def process_csv_to_fhir(incoming_message_body: dict) -> None:
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    """
    try:
        interim_message_body = file_level_validation(incoming_message_body=incoming_message_body)
    except (InvalidHeaders, NoOperationPermissions, Exception):  # pylint: disable=broad-exception-caught
        # If the file is invalid, processing should cease immediately
        return

    file_id = interim_message_body.get("message_id")
    vaccine = interim_message_body.get("vaccine")
    supplier = interim_message_body.get("supplier")
    file_key = interim_message_body.get("file_key")
    allowed_operations = interim_message_body.get("allowed_operations")
    created_at_formatted_string = interim_message_body.get("created_at_formatted_string")
    csv_reader = interim_message_body.get("csv_dict_reader")

    target_disease = map_target_disease(vaccine)
    row_count = 0
    ingestion_start_time = time.time()
    logger.info(ingestion_progress(
                    finished=False,
                    message_body=interim_message_body))

    for row in csv_reader:
        row_count += 1
        row_id = f"{file_id}^{row_count}"
        logger.info("MESSAGE ID : %s", row_id)

        # Process the row to obtain the details needed for the message_body and ack file
        details_from_processing = process_row(target_disease, allowed_operations, row)

        # Create the message body for sending
        outgoing_message_body = {
            "row_id": row_id,
            "file_key": file_key,
            "supplier": supplier,
            "vax_type": vaccine,
            "created_at_formatted_string": created_at_formatted_string,
            **details_from_processing,
        }

        send_to_kinesis(supplier, outgoing_message_body, vaccine)

        logger.info("Total rows processed: %s", row_count)

    logger.info(ingestion_progress(
                    finished=True,
                    message_body=interim_message_body,
                    row_count=row_count,
                    start_time=ingestion_start_time))


def main(event: str) -> None:
    """Process each row of the file"""
    logger.info("task started")
    start = time.time()
    try:
        process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)
    end = time.time()
    logger.info("Total time for completion: %ss", round(end - start, 5))


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
